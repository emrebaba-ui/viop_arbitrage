import pandas as pd
from itertools import combinations

class FutureSpreadEngine:
    def __init__(self, target_rate=0.35, min_volume_tl=50000, commission_rate=0.001):
        self.target_rate = target_rate 
        self.min_volume_tl = min_volume_tl
        self.commission_rate = commission_rate

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty: 
            return pd.DataFrame()
            
        df = df.dropna(subset=['bid', 'ask', 'volume_lot', 'Req_Capital']).copy()
        df = df[(df['bid'] > 0) & (df['ask'] > 0)]
        
        is_usd = df['BaseAsset'].str.endswith('USD')
        fx_rate = df['USD_Rate'].where(is_usd, 1.0)
        
        df['Mid_Price'] = (df['bid'] + df['ask']) / 2
        df['Volume_TL'] = df['volume_lot'] * df['Mid_Price'] * df['Multiplier'] * fx_rate
        df = df[df['Volume_TL'] >= self.min_volume_tl].copy()
        
        if df.empty:
            return df
            
        spread_opportunities = []
        
        for asset, group in df.groupby('BaseAsset'):
            if len(group) < 2: 
                continue
                
            asset_rate = 0.04 if asset.endswith('USD') else self.target_rate # type: ignore
                
            group = group.sort_values('Days')
            contracts = group.to_dict('records')
            
            for c1, c2 in combinations(contracts, 2):
                days_diff = c2['Days'] - c1['Days']
                if days_diff <= 0: continue
                
                multiplier = c1['Multiplier']
                is_usd_asset = asset.endswith('USD') # type: ignore
                fx = c1.get('USD_Rate', 1.0) if is_usd_asset else 1.0

                convergence_ratio = c1['Days'] / c2['Days'] 
                
                # --- BUY SPREAD ---
                implied_rate_buy = (c2['ask'] / c1['bid']) ** (365 / days_diff) - 1
                
                fair_far_buy_spread = c1['bid'] * ((1 + asset_rate) ** (days_diff / 365))
                total_mispricing_buy = fair_far_buy_spread - c2['ask']
                
                # total divergence * time at hand
                gross_profit_buy = total_mispricing_buy * convergence_ratio * multiplier * fx
                comm_buy = (c1['bid'] + c2['ask']) * multiplier * self.commission_rate * fx
                net_profit_buy = gross_profit_buy - comm_buy
                
                # --- SELL SPREAD ---
                implied_rate_sell = (c2['bid'] / c1['ask']) ** (365 / days_diff) - 1
                
                fair_far_sell_spread = c1['ask'] * ((1 + asset_rate) ** (days_diff / 365))
                total_mispricing_sell = c2['bid'] - fair_far_sell_spread
                
                # total divergence * time at hand
                gross_profit_sell = total_mispricing_sell * convergence_ratio * multiplier * fx
                comm_sell = (c1['ask'] + c2['bid']) * multiplier * self.commission_rate * fx
                net_profit_sell = gross_profit_sell - comm_sell
                
                if net_profit_buy > 0 and net_profit_buy > net_profit_sell:
                    near_action, near_price = f'SELL: {c1['Contract']}', c1['bid']
                    far_action, far_price = f'BUY: {c2['Contract']}', c2['ask']
                    net_profit = net_profit_buy
                    total_comm = comm_buy
                    type_str = "BUY SPREAD"
                    final_implied = implied_rate_buy
                elif net_profit_sell > 0 and net_profit_sell > net_profit_buy:
                    near_action, near_price = f'BUY: {c1['Contract']}', c1['ask']
                    far_action, far_price = f'SELL: {c2['Contract']}', c2['bid']
                    net_profit = net_profit_sell
                    total_comm = comm_sell
                    type_str = "SELL SPREAD"
                    final_implied = implied_rate_sell
                else:
                    continue
                
                req_capital = max(c1['Req_Capital'], c2['Req_Capital'])
                holding_days = max(c1['Days'], 1) 
                daily_profit = net_profit / holding_days
                daily_roi = daily_profit * 100 / req_capital
                
                spread_opportunities.append({
                    'Asset': asset,
                    'Type': type_str,
                    'Near_Action': f"{near_action} @ {near_price:.2f}",
                    'Far_Action': f"{far_action} @ {far_price:.2f}",
                    'Hold_Days': holding_days,
                    'Implied_%': final_implied * 100,
                    'Req_Capital': req_capital,
                    'Total_Comm': total_comm,
                    'Net_Profit': net_profit,
                    'Daily_Profit': daily_profit,
                    'Daily_ROI_%': daily_roi
                })
                
        results_df = pd.DataFrame(spread_opportunities)
        if not results_df.empty:
            results_df = results_df.sort_values(by='Daily_ROI_%', ascending=False)
            
        return results_df
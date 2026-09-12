import pandas as pd
from itertools import combinations

from config import *


class FutureSpreadEngine:
    def __init__(self, target_rate=ANNUAL_RISK_FREE_RATE, min_volume_tl=SPREAD_MIN_VOLUME_TL, commission_rate=COMMISSION_RATE):
        self.target_rate = target_rate 
        self.min_volume_tl = min_volume_tl
        self.commission_rate = commission_rate

    def process(self, df: pd.DataFrame | None) -> pd.DataFrame:
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

            asset_key = str(asset).upper()
            asset_rate = 0.04 if asset_key.endswith('USD') else self.target_rate 
                
            group = group.sort_values('Days')
            contracts = group.to_dict('records')
            
            for c1, c2 in combinations(contracts, 2):
                days_diff = c2['Days'] - c1['Days']
                if days_diff <= 0: continue
                
                multiplier = c1['Multiplier']
                is_usd_asset = asset_key.endswith('USD')
                fx = c1.get('USD_Rate', 1.0) if is_usd_asset else 1.0

                if multiplier == 100: # Stocks must be sold ~3 days earlier
                    convergence_ratio = (c1['Days'] - 3) / (c2['Days'])
                else:
                    convergence_ratio = c1['Days'] / c2['Days'] 
                
                # -------------- BUY SPREAD --------------
                implied_rate_buy = (c2['ask'] / c1['bid']) ** (365 / days_diff) - 1
                
                theoretical_price_buy = c1['bid'] * ((1 + asset_rate) ** (days_diff / 365))
                spread_buy = theoretical_price_buy - c2['ask']
                
                gross_profit_buy = spread_buy * multiplier * fx
                gross_profit_buy_conv = gross_profit_buy * convergence_ratio
                comm_buy = (c1['bid'] + c2['ask']) * multiplier * self.commission_rate * fx
                pot_profit_buy = gross_profit_buy - comm_buy
                net_profit_buy = gross_profit_buy_conv - comm_buy
                
                # -------------- SELL SPREAD --------------
                implied_rate_sell = (c2['bid'] / c1['ask']) ** (365 / days_diff) - 1
                
                theoretical_price_sell = c1['ask'] * ((1 + asset_rate) ** (days_diff / 365))
                spread_sell = c2['bid'] - theoretical_price_sell
                
                gross_profit_sell = spread_sell * multiplier * fx
                gross_profit_sell_conv = gross_profit_sell * convergence_ratio
                comm_sell = (c1['ask'] + c2['bid']) * multiplier * self.commission_rate * fx
                pot_profit_sell = gross_profit_sell - comm_sell
                net_profit_sell = gross_profit_sell_conv - comm_sell
                
                if net_profit_buy > 0 and net_profit_buy > net_profit_sell:
                    near_action, near_price = f'SELL: {c1['Contract']}', c1['bid']
                    far_action, far_price = f'BUY: {c2['Contract']}', c2['ask']
                    net_profit = net_profit_buy
                    pot_profit = pot_profit_buy
                    total_comm = comm_buy
                    final_implied = implied_rate_buy
                elif net_profit_sell > 0 and net_profit_sell > net_profit_buy:
                    near_action, near_price = f'BUY: {c1['Contract']}', c1['ask']
                    far_action, far_price = f'SELL: {c2['Contract']}', c2['bid']
                    net_profit = net_profit_sell
                    pot_profit = pot_profit_sell
                    total_comm = comm_sell
                    final_implied = implied_rate_sell
                else:
                    continue
                
                req_capital = max(c1['Req_Capital'], c2['Req_Capital'])
                holding_days = c1['Days']
                daily_profit = net_profit / holding_days
                daily_roi = daily_profit * 100 / req_capital
                
                spread_opportunities.append({
                    'Asset': asset,
                    'Near_Action': f"{near_action} @ {near_price:.2f}",
                    'Far_Action': f"{far_action} @ {far_price:.2f}",
                    'Hold': holding_days,
                    'Implied_%': final_implied * 100,
                    'Req_Capital': req_capital,
                    'Total_Comm': total_comm,
                    'Net_Profit': net_profit,
                    'Pot_Profit': pot_profit,
                    'Daily_Profit': daily_profit,
                    'Daily_ROI_%': daily_roi
                })
                
        results_df = pd.DataFrame(spread_opportunities)
        if not results_df.empty:
            results_df = results_df.sort_values(by='Daily_ROI_%', ascending=False)
            
        return results_df
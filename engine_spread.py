import pandas as pd
from itertools import combinations

class FutureSpreadEngine:
    def __init__(self, min_volume_tl=50000, commission_rate=0.001):
        self.min_volume_tl = min_volume_tl
        self.commission_rate = commission_rate

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty: 
            return pd.DataFrame()
            
        # Filter valid rows
        df = df.dropna(subset=['underlying_close', 'bid', 'ask', 'volume_lot'])
        df = df[(df['underlying_close'] > 0) & (df['bid'] > 0) & (df['ask'] > 0)].copy()
        
        # Volume filter
        df['Mid_Price'] = (df['bid'] + df['ask']) / 2
        df['Volume_TL'] = df['volume_lot'] * df['Mid_Price']
        df = df[df['Volume_TL'] >= self.min_volume_tl].copy()
        
        if df.empty:
            return df
            
        # Calculate implied interest rates
        df['Implied_Rate_Bid'] = ((df['bid'] / df['underlying_close']) - 1) * (365 / df['Days'])
        df['Implied_Rate_Ask'] = ((df['ask'] / df['underlying_close']) - 1) * (365 / df['Days'])
        
        spread_opportunities = []
        
        for asset, group in df.groupby('BaseAsset'):
            if len(group) < 2: 
                continue
                
            group = group.sort_values('Days')
            contracts = group.to_dict('records')
            
            for c1, c2 in combinations(contracts, 2):
                # Scenario 1: Buy Near (Ask), Sell Far (Bid)
                rate_diff_1 = c2['Implied_Rate_Bid'] - c1['Implied_Rate_Ask']
                
                # Scenario 2: Sell Near (Bid), Buy Far (Ask)
                rate_diff_2 = c1['Implied_Rate_Bid'] - c2['Implied_Rate_Ask']
                
                if rate_diff_1 > 0 and rate_diff_1 > rate_diff_2:
                    rate_diff = rate_diff_1
                    near_action, near_price = 'BUY', c1['ask']
                    far_action, far_price = 'SELL', c2['bid']
                elif rate_diff_2 > 0 and rate_diff_2 > rate_diff_1:
                    rate_diff = rate_diff_2
                    near_action, near_price = 'SELL', c1['bid']
                    far_action, far_price = 'BUY', c2['ask']
                else:
                    continue # Skip if no profit
                
                # Calculate metrics
                multiplier = c1['Multiplier']
                underlying_close = c1['underlying_close']
                
                total_comm = (near_price + far_price) * multiplier * self.commission_rate
                daily_return = (rate_diff / 365) * underlying_close * multiplier
                
                days_to_breakeven = total_comm / daily_return if daily_return > 0 else float('inf')
                
                spread_opportunities.append({
                    'Asset': asset,
                    'Near_Contract': c1['Contract'],
                    'Near_Action': f"{near_action} @ {near_price:.2f}",
                    'Far_Contract': c2['Contract'],
                    'Far_Action': f"{far_action} @ {far_price:.2f}",
                    'Rate_Diff_%': rate_diff * 100,
                    'Total_Comm': total_comm,
                    'Daily_Return': daily_return,
                    'Breakeven_Days': days_to_breakeven
                })
                
        results_df = pd.DataFrame(spread_opportunities)
        if not results_df.empty:
            results_df = results_df.sort_values(by='Breakeven_Days', ascending=True)
            
        return results_df
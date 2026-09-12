import pandas as pd
import numpy as np

class PositionTracker:
    def __init__(self, trades_file='trades.csv'):
        self.trades_file = trades_file

    def parse_action(self, action_str):
        # parse format: "SELL: F_HALKB0926 @ 50.92"
        try:
            parts = str(action_str).replace(':', '').split()
            return parts[0], parts[1], float(parts[3])
        except (IndexError, ValueError, AttributeError):
            return None, None, 0.0

    def print_status(self, live_data: pd.DataFrame, spread_results: pd.DataFrame):
        # load trades
        try:
            df_trades = pd.read_csv(self.trades_file)
            df_trades.columns = df_trades.columns.str.strip()
        except FileNotFoundError:
            print(f"No {self.trades_file}")
            return

        # filter open positions
        open_pos = df_trades[df_trades['Result'].fillna('').str.strip() == ''].copy()
        if open_pos.empty:
            return
            
        # extract contract names for easy matching if spread_results exists
        if spread_results is not None and not spread_results.empty:
            spread_results = spread_results.copy()
            spread_results['Near_Contract'] = spread_results['Near_Action'].apply(lambda x: self.parse_action(x)[1])
            spread_results['Far_Contract'] = spread_results['Far_Action'].apply(lambda x: self.parse_action(x)[1])

        results = []
        for _, row in open_pos.iterrows():
            amount = float(row['Amount'])
            near_type, near_contract, near_entry = self.parse_action(row['Near Action'])
            far_type, far_contract, far_entry = self.parse_action(row['Far Action'])

            # get live data for PnL calculation
            near_market = live_data[live_data['Contract'] == near_contract]
            far_market = live_data[live_data['Contract'] == far_contract]

            if near_market.empty or far_market.empty:
                continue

            near_live = near_market.iloc[0]
            far_live = far_market.iloc[0]
            multiplier = near_live.get('Multiplier', 100)

            # calculate PnL using live bid/ask
            near_close = near_live['ask'] if near_type == 'SELL' else near_live['bid']
            far_close = far_live['ask'] if far_type == 'SELL' else far_live['bid']

            near_pnl = (near_entry - near_close) if near_type == 'SELL' else (near_close - near_entry)
            far_pnl = (far_entry - far_close) if far_type == 'SELL' else (far_close - far_entry)
            gross_pnl = (near_pnl + far_pnl) * multiplier * amount

            # get engine data from spread_results
            implied = np.nan
            total_comm = np.nan
            net_profit = np.nan
            pot_profit = np.nan

            if spread_results is not None and not spread_results.empty:
                match = spread_results[
                    (spread_results['Near_Contract'] == near_contract) & 
                    (spread_results['Far_Contract'] == far_contract)
                ]
                if not match.empty:
                    # columns must match engine_spread.py outputs
                    implied = match.iloc[0].get('Implied_%', np.nan)
                    total_comm = match.iloc[0].get('Total_Comm', np.nan)
                    net_profit = match.iloc[0].get('Net_Profit', np.nan)
                    pot_profit = match.iloc[0].get('Pot_Profit', np.nan)

            results.append({
                'Date': row['Date'],
                'Pair': f"{row['Near Action']}, {row['Far Action']}",
                'Lot': amount,
                'Live_PnL': gross_pnl - total_comm * amount * 2,
                'Implied_%': implied,
                'Net_Profit': net_profit,
                'Pot_Profit': pot_profit
            })

        return pd.DataFrame(results)
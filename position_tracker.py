import re
import pandas as pd

class PositionTracker:
    def __init__(self, trades_file="trades.csv"):
        self.trades_file = trades_file

    def _parse_action(self, action_str: str):
        # Parses "SELL: F_HALKB0926 @ 50.92" -> ('SELL', 'F_HALKB0926', 50.92)
        match = re.search(r'(BUY|SELL):\s*([A-Za-z0-9_]+)\s*@\s*([\d.]+)', str(action_str))
        if match:
            act, contract, price = match.groups()
            return act.upper(), contract, float(price)
        return None, None, 0.0

    def track_open_positions(self, spread_df: pd.DataFrame, market_df: pd.DataFrame):
        """
        Matches open trades in trades.csv with engine_spread output.
        """
        try:
            trades_df = pd.read_csv(self.trades_file)
        except Exception:
            return

        # Filter open positions (Result column is empty/NaN)
        open_trades = trades_df[trades_df['Result'].isna() | (trades_df['Result'].astype(str).str.strip() == '')]
        if open_trades.empty or spread_df is None or spread_df.empty:
            return

        # Index spread_df by (Near_Contract, Far_Contract) for O(1) fast lookup
        spread_map = spread_df.set_index(['Near_Contract', 'Far_Contract']).to_dict('index')
        market_map = market_df.set_index('Contract').to_dict('index') if market_df is not None else {}

        for _, row in open_trades.iterrows():
            near_act, near_code, near_entry = self._parse_action(row['Near Action'])
            far_act, far_code, far_entry = self._parse_action(row['Far Action'])

            key = (near_code, far_code)
            if key not in spread_map:
                continue

            spread_info = spread_map[key]
            amount = float(row.get('Amount', 1))

            # Extract current prices evaluated by engine_spread (Near_Action: "SELL @ 50.92")
            curr_near = float(re.search(r'@\s*([\d.]+)', str(spread_info['Near_Action'])).group(1)) # type: ignore
            curr_far = float(re.search(r'@\s*([\d.]+)', str(spread_info['Far_Action'])).group(1))   # type: ignore

            # Multiplier and FX lookup from market_df for PnL scaling
            mkt = market_map.get(near_code, {})
            mult = mkt.get('Multiplier', 100)
            fx = mkt.get('USD_Rate', 1.0) if mkt.get('BaseAsset', '').endswith('USD') else 1.0

            # Unrealized PnL (Anlık kâr/zarar)
            pnl_near = (near_entry - curr_near) if near_act == 'SELL' else (curr_near - near_entry)
            pnl_far = (curr_far - far_entry) if far_act == 'BUY' else (far_entry - curr_far)
            pnl_total = (pnl_near + pnl_far) * mult * amount * fx

            yield {
                'Date': row['Date'],
                'Near_Contract': near_code,
                'Far_Contract': far_code,
                'Amount': amount,
                'Implied_%': round(spread_info.get('Implied_%', 0.0), 2),
                'Net_Profit': round(pnl_total, 2),
                'Pot_Profit': round(spread_info.get('Net_Profit', 0.0) * amount, 2),
                'PNL_Near_Far_Total': (pnl_near, pnl_far, pnl_total)
            }

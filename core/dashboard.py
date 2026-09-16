import subprocess
import time
import pandas as pd
from datetime import timedelta
from email.utils import parsedate_to_datetime

from config import *
from core.data import MarketDataService
from core.engine_spot import SpotFutureEngine
from core.engine_spread import FutureSpreadEngine
from core.position_tracker import PositionTracker
from core.storage import StorageManager
from core.linux_notifier import LinuxNotifier


pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

def get_asset_class(base_asset: str) -> str:
    if base_asset in CURRENCIES: return 'CURRENCY'
    if base_asset in INDICES: return 'INDEX'
    if base_asset in METALS: return 'METAL'
    return 'STOCK'

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or ASSET_FILTER == 'ALL':
        return df
    df['Asset_Class'] = df['BaseAsset'].apply(get_asset_class)
    return df[df['Asset_Class'].isin(ASSET_FILTER)].copy()

def parse_and_adjust_time(server_time_str: str) -> str:
    if not server_time_str: return "Unknown Time"
    try:
        server_dt = parsedate_to_datetime(server_time_str)
        local_dt = server_dt + timedelta(hours=3)
        return local_dt.strftime('%Y-%m-%d %H:%M:%S (GMT+3)')
    except Exception:
        return server_time_str

def main():
    data_service = MarketDataService()
    spot_engine = SpotFutureEngine()
    spread_engine = FutureSpreadEngine()
    tracker = PositionTracker()
    storage = StorageManager()
    notifier = LinuxNotifier()

    while True:
        try:
            df, server_time_str = data_service.get_prepared_data()
            subprocess.run('clear')
            
            current_time = parse_and_adjust_time(server_time_str)
            print(f" Mode: {DISPLAY_MODE} | Assets: {ASSET_FILTER} | Last Update: {current_time}")
            print()
            
            if df.empty:
                print("No data available from API.")
            else:
                filtered_df = filter_dataframe(df)
                
                print("--- SPOT-FUTURE OPPORTUNITIES (TOP 10) ---")
                spot_results = spot_engine.process(filtered_df)
                if not spot_results.empty:
                    cols = ['Contract', 'Spot_Price', 'Future_Price', 'Days', 'Total_Comm', 'Net_Profit', 'Req_Capital', 'Arb_Monthly_%']
                    print(spot_results[cols].head(10).round(2).to_string(index=False))
                else:
                    print("No profitable Spot-Future opportunities found.")
                print()
                    
                print("--- FUTURE SPREAD OPPORTUNITIES (TOP 30) ---")
                spread_results = spread_engine.process(filtered_df)
                if not spread_results.empty:
                    cols = ['Near_Action', 'Far_Action', 'Hold', 'Implied_%', 'Net_Profit', 'Pot_Profit', 'Req_Capital', 'Daily_Profit', 'Daily_ROI_%']
                    print(spread_results[cols].head(30).round(2).to_string(index=False))
                    storage.save(spread_results)
                else:
                    print("No profitable Future Spread opportunities found.")
                print()

                res_df = tracker.print_status(filtered_df, spread_results)
                if res_df is not None and not res_df.empty:
                    print("--- OPEN POSITIONS STATUS ---")
                    print(res_df.fillna('-').round(2).to_string(index=False))
                    
                    # NOTIFICATION CHECK
                    for _, row in res_df.iterrows():
                        pot_profit = row['Pot_Profit']
                        if pd.notna(pot_profit) and pot_profit < 0:
                            msg = f"Arbitrage edge is totally consumed for {row['Pair']}"
                            notifier.send("⚠️ Arbitrage Alert", msg)

        except Exception as e:
            print(f"Error: {e}")
            
        time.sleep(FREQUENCY)

if __name__ == "__main__":
    main()
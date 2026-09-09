import os
import time
import pandas as pd
from datetime import timedelta
from email.utils import parsedate_to_datetime

from data import MarketDataService
from engine_spot import SpotFutureEngine
from engine_spread import FutureSpreadEngine

DISPLAY_MODE = 'ALL'
ASSET_FILTER = 'ALL' 

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

CURRENCIES = {'USDTRY', 'EURTRY', 'EURUSD', 'GBPUSD', 'CNHTRY', 'RUBTRY'}
INDICES = {'XU030', 'XLBNK', 'X10XB', 'XSD25', 'SASX10'}
METALS = {'XAUUSD', 'XAUTRY', 'XPTUSD', 'XPDUSD', 'XAGUSD', 'XAGTRY', 'XCUUSD'}

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
    
    while True:
        try:
            df, server_time_str = data_service.get_prepared_data()
            os.system('clear')
            
            current_time = parse_and_adjust_time(server_time_str)
            print("=" * 125)
            print(f" ARBITRAGE DASHBOARD | Last Update: {current_time}")
            print(f" Mode: {DISPLAY_MODE} | Assets: {ASSET_FILTER}")
            print("=" * 125 + "\n")
            
            if df.empty:
                print("No data available from API.")
            else:
                filtered_df = filter_dataframe(df)
                
                if DISPLAY_MODE in ['ALL', 'SPOT']:
                    print("--- SPOT-FUTURE OPPORTUNITIES (TOP 20) ---")
                    spot_results = spot_engine.process(filtered_df)
                    if not spot_results.empty:
                        cols = ['Contract', 'Spot_Price', 'Future_Price', 'Days', 'Total_Comm', 'Net_Profit', 'Req_Capital', 'Arb_Monthly_%']
                        print(spot_results[cols].head(20).round(2).to_string(index=False))
                    else:
                        print("No profitable Spot-Future opportunities found.")
                    print("\n")
                    
                if DISPLAY_MODE in ['ALL', 'SPREAD']:
                    print("--- FUTURE SPREAD OPPORTUNITIES (TOP 20) ---")
                    spread_results = spread_engine.process(filtered_df)
                    if not spread_results.empty:
                        cols = ['Asset', 'Type', 'Near_Action', 'Far_Action', 'Hold_Days', 'Implied_%', 'Net_Profit', 'Req_Capital', 'Daily_Profit', 'Daily_ROI']
                        print(spread_results[cols].head(20).round(2).to_string(index=False))
                    else:
                        print("No profitable Future Spread opportunities found.")
                        
        except Exception as e:
            print(f"Error: {e}")
            
        time.sleep(3)

if __name__ == "__main__":
    main()
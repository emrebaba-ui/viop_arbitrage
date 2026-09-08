import os
import time
import pandas as pd
from datetime import timedelta
from email.utils import parsedate_to_datetime

# Import our custom modules
from data import MarketDataService
from engine_spot import SpotFutureEngine
from engine_spread import FutureSpreadEngine

# ==========================================
# CONFIGURATION & FILTERS
# ==========================================
# Display Modes: 'ALL', 'SPOT', 'SPREAD'
DISPLAY_MODE = 'ALL'

# Asset Filters: 'ALL' or a list like ['CURRENCY', 'INDEX', 'STOCK']
ASSET_FILTER = 'ALL' 

# Set pandas to show all columns without wrapping in terminal
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
# ==========================================

CURRENCIES = {'USDTRY', 'EURTRY', 'EURUSD', 'GBPUSD', 'CNHTRY', 'RUBTRY'}
INDICES = {'XU030', 'XLBNK', 'X10XB', 'XSD25'}

def get_asset_class(base_asset: str) -> str:
    # Classify assets for filtering
    if base_asset in CURRENCIES: return 'CURRENCY'
    if base_asset in INDICES: return 'INDEX'
    return 'STOCK'

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Apply user-defined asset filters
    if df.empty or ASSET_FILTER == 'ALL':
        return df
        
    df['Asset_Class'] = df['BaseAsset'].apply(get_asset_class)
    return df[df['Asset_Class'].isin(ASSET_FILTER)].copy()

def parse_and_adjust_time(server_time_str: str) -> str:
    # Convert GMT server time to GMT+3
    if not server_time_str:
        return "Unknown Time"
    try:
        server_dt = parsedate_to_datetime(server_time_str)
        local_dt = server_dt + timedelta(hours=3) # Add 3 hours for GMT+3
        return local_dt.strftime('%Y-%m-%d %H:%M:%S (GMT+3)')
    except Exception:
        return server_time_str

def main():
    data_service = MarketDataService()
    spot_engine = SpotFutureEngine()
    spread_engine = FutureSpreadEngine()
    
    while True:
        try:
            # 1. Fetch Data & Time
            df, server_time_str = data_service.get_prepared_data()
            
            # 2. Clear Terminal (Linux Mint)
            os.system('clear')
            
            # 3. Print Header
            current_time = parse_and_adjust_time(server_time_str)
            print("=" * 60)
            print(f" ARBITRAGE DASHBOARD | Last Update: {current_time}")
            print(f" Mode: {DISPLAY_MODE} | Assets: {ASSET_FILTER}")
            print("=" * 60 + "\n")
            
            if df.empty:
                print("No data available from API.")
            else:
                # Apply Asset Filter
                filtered_df = filter_dataframe(df)
                
                # 4. Spot-Future Engine Output
                if DISPLAY_MODE in ['ALL', 'SPOT']:
                    print("--- SPOT-FUTURE OPPORTUNITIES (TOP 20) ---")
                    spot_results = spot_engine.process(filtered_df)
                    
                    if not spot_results.empty:
                        # Select specific columns to fit the terminal nicely
                        cols = ['Contract', 'Spot_Price', 'Future_Price', 'Days', 'Total_Comm', 'Gross_Monthly_%', 'Net_Profit', 'Req_Capital']
                        print(spot_results[cols].head(20).round(2).to_string(index=False))
                    else:
                        print("No profitable Spot-Future opportunities found.")
                    print("\n")
                    
                # 5. Future Spread Engine Output
                if DISPLAY_MODE in ['ALL', 'SPREAD']:
                    print("--- FUTURE SPREAD OPPORTUNITIES (TOP 20) ---")
                    spread_results = spread_engine.process(filtered_df)
                    
                    if not spread_results.empty:
                        # Select specific columns to fit the terminal nicely
                        cols = ['Near_Contract', 'Near_Action', 'Far_Contract', 'Far_Action', 'Rate_Diff_%', 'Total_Comm', 'Daily_Return', 'Breakeven_Days']
                        print(spread_results[cols].head(20).round(2).to_string(index=False))
                    else:
                        print("No profitable Future Spread opportunities found.")
                        
        except Exception as e:
            print(f"An error occurred: {e}")
            
        # Wait 3 seconds before next cycle
        time.sleep(3)

if __name__ == "__main__":
    main()
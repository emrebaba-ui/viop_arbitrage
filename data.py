import pandas as pd
from curl_cffi import requests
from datetime import datetime
import calendar
import re

# --- Pure Functions (FP Approach) ---

def get_multiplier(base_asset: str) -> int:
    # Determine contract multiplier based on asset type
    currencies = {'USDTRY', 'EURTRY', 'EURUSD', 'GBPUSD', 'CNHTRY', 'RUBTRY'}
    indices = {'XU030', 'XLBNK', 'X10XB', 'XSD25'}
    
    if base_asset in currencies: 
        return 1000
    elif base_asset in indices: 
        return 10
    return 100

def calculate_days_to_exp(contract_code: str, current_date: datetime) -> int:
    # Extract expiration date from contract code and calculate days left
    match = re.search(r'\d{4,6}$', contract_code)
    if not match: 
        return 1
        
    mmyy = match.group()
    month = int(mmyy[-4:-2])
    year = int("20" + mmyy[-2:])
    _, last_day = calendar.monthrange(year, month)
    
    target_date = datetime(year, month, last_day)
    days_left = (target_date - current_date).days
    
    return max(days_left, 1)


# --- Data Service (OOP Approach) ---

class MarketDataService:
    def __init__(self):
        self.url = "https://markets.fintables.com/barbar/server/?type=future"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Origin": "https://fintables.com",
            "Referer": "https://fintables.com/"
        }

    def fetch_raw_data(self) -> tuple:
        response = requests.get(self.url, headers=self.headers, impersonate="chrome")
        if response.status_code != 200: 
            return pd.DataFrame(), None
            
        data = response.json()
        server_time_str = response.headers.get('Date') # Gets GMT server time
        
        df = pd.DataFrame([
            {"Contract": code, **dict(zip(data["columns"], vals))}
            for code, vals in data["results"].items()
        ])
        return df, server_time_str

    def get_prepared_data(self) -> tuple:
        df, server_time = self.fetch_raw_data()
        
        if df.empty:
            return df, None
            
        current_date = datetime.now()
        df['BaseAsset'] = df['Contract'].apply(lambda x: re.sub(r'^(?:TM_)?F_|\d{4,6}$', '', x))
        df['Multiplier'] = df['BaseAsset'].apply(get_multiplier)
        df['Days'] = df['Contract'].apply(lambda x: calculate_days_to_exp(x, current_date))
        
        return df, server_time

# --- Testing the Service ---
if __name__ == "__main__":
    service = MarketDataService()
    prepared_df = service.get_prepared_data()[0]
    server_time = service.get_prepared_data()[1]
    
    if not prepared_df.empty:
        print("Data fetched and prepared successfully.")
        print(prepared_df[['Contract', 'BaseAsset', 'Multiplier', 'Days']].head())
        print(f"Server Time: {server_time}")
    else:
        print("Failed to fetch data.")
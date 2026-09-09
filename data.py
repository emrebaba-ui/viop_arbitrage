import pandas as pd
from curl_cffi import requests
from datetime import datetime
import calendar
import re

def get_base_asset(contract_code: str) -> str:
    # Remove prefix
    c = re.sub(r'^(?:TM_)?F_', '', contract_code)
    
    # Check known indices with numbers
    known_indices = ['XU030', 'XLBNK', 'X10XB', 'XSD25', 'SASX10']
    for idx in known_indices:
        if c.startswith(idx): 
            return idx
            
    # For standard assets (HEKTS, USDTRY, XAUUSD), extract letters
    m = re.match(r'^([A-Za-z]+)', c)
    if m: 
        return m.group(1)
        
    return c[:-4] # Fallback

def get_multiplier(base_asset: str) -> int:
    currencies = {'USDTRY', 'EURTRY', 'EURUSD', 'GBPUSD', 'CNHTRY', 'RUBTRY'}
    indices = {'XU030', 'XLBNK', 'X10XB', 'XSD25', 'SASX10'}
    metals_1 = {'XAUUSD', 'XAUTRY', 'XPTUSD', 'XPDUSD', 'XCUUSD'}
    metals_10 = {'XAGUSD', 'XAGTRY'}
    
    if base_asset in currencies: return 1000
    elif base_asset in indices: return 10
    elif base_asset in metals_1: return 1
    elif base_asset in metals_10: return 10
    return 100

def calculate_days_to_exp(contract_code: str, current_date: datetime) -> int:
    match = re.search(r'\d{4,6}$', contract_code)
    if not match: return 1
        
    mmyy = match.group()
    month = int(mmyy[-4:-2])
    year = int("20" + mmyy[-2:])
    _, last_day = calendar.monthrange(year, month)
    
    target_date = datetime(year, month, last_day)
    return max((target_date - current_date).days, 1)

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
        server_time_str = response.headers.get('Date')
        
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
        df['BaseAsset'] = df['Contract'].apply(get_base_asset)
        df['Multiplier'] = df['BaseAsset'].apply(get_multiplier)
        df['Days'] = df['Contract'].apply(lambda x: calculate_days_to_exp(x, current_date))
        
        usdtry_df = df[df['BaseAsset'] == 'USDTRY'].sort_values('Days')
        if not usdtry_df.empty:
            best_row = usdtry_df.iloc[0]
            usd_rate = best_row['bid'] if pd.notna(best_row['bid']) and best_row['bid'] > 0 else best_row['underlying_close']
        else:
            usd_rate = 1.0
            
        df['USD_Rate'] = usd_rate
        df['Req_Capital'] = df['psr_close'].astype(float)
        
        is_usd_based = df['BaseAsset'].str.endswith('USD')
        df.loc[is_usd_based, 'Req_Capital'] = df['Req_Capital'] * df['USD_Rate']
        
        return df, server_time
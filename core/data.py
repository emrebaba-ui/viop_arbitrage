import logging
import pandas as pd
import time
from curl_cffi import requests
from datetime import datetime

from config import *
from tools.fin_auth import FintablesAuth
from core.data_standardizer import *

# --- LOGGING ---
logging.basicConfig(
    filename=ERROR_LOG_FILE_PATH,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class MarketDataService:
    def __init__(self):
        self.url = URL
        self.headers = HEADERS
        self.max_retries = BACKOFF_MAX_RETRIES

    def _refresh_security_headers(self):
        auth = FintablesAuth()
        fresh_headers = auth.get_fresh_headers()
        
        if fresh_headers:
            self.headers.update(fresh_headers)
            print("Header information was refreshed.")
        else:
            logging.error("Security headers could not be obtained.")
        
    def fetch_raw_data(self) -> tuple:
        retries = 1
        backoff_time = BACKOFF_TIME
        
        while retries <= self.max_retries:
            try:
                self._refresh_security_headers()
                response = requests.get(self.url, headers=self.headers, impersonate="chrome")
                
                if response.status_code == 200:
                    data = response.json()
                    server_time_str = response.headers.get('Date')
                    
                    df = pd.DataFrame([
                        {"Contract": code, **dict(zip(data["columns"], vals))}
                        for code, vals in data["results"].items()
                    ])
                    return df, server_time_str

                elif response.status_code in [401, 403]:
                    logging.warning(f"Authentication failed ({response.status_code}). Refreshing headers...")
                    print(f"Authentication failed ({response.status_code}). Refreshing headers...")

                else:
                    print(f"API Error: Status Code {response.status_code}. Attempt {retries}/{self.max_retries}")
                    logging.error(f"API Error: Status Code {response.status_code}. Attempt {retries}/{self.max_retries}")
                    
            except Exception as e:
                # Physical errors
                logging.error(f"Connection Failed: {e}. Attempt {retries}/{self.max_retries}")
                
            time.sleep(backoff_time)
            backoff_time *= 2
            retries += 1

        return pd.DataFrame(), None

    def get_prepared_data(self) -> tuple:
        df, server_time = self.fetch_raw_data()
        
        if df.empty:
            return df, None
            
        current_date = datetime.now()
        df['BaseAsset'] = df['Contract'].apply(get_base_asset)
        df['Multiplier'] = df['BaseAsset'].apply(get_multiplier)
        df['Target_Rate'] = df['BaseAsset'].apply(calculate_target_rate)
        df['Days'] = df['Contract'].apply(lambda x: calculate_days_to_exp(x, current_date))
        df = standardize_capital(df)
        
        return df, server_time
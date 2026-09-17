import pandas as pd
import re
import calendar
from datetime import datetime

from config import *


def get_base_asset(contract_code: str) -> str:
    # Remove prefix
    c = re.sub(r'^(?:TM_)?F_', '', contract_code)
    
    # Check known indices with numbers
    for idx in INDICES:
        if c.startswith(idx): 
            return idx
            
    # For standard assets (HEKTS, USDTRY, XAUUSD), extract letters
    m = re.match(r'^([A-Za-z]+)', c)
    if m: 
        return m.group(1)
        
    return c[:-4] # Fallback

def get_multiplier(base_asset: str) -> int:
    metals_10 = {'XAGUSD', 'XAGTRY'}
    
    if base_asset in CURRENCIES: return 1000
    elif base_asset in INDICES: return 10
    elif base_asset in metals_10: return 10
    elif base_asset in METALS: return 1
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

def calculate_target_rate(base_asset: str) -> float:
    asset_clean = base_asset[:6] 
    
    is_currency = any(base_asset.startswith(c) for c in CURRENCIES)
    is_metal = any(base_asset.startswith(m[:6]) for m in METALS)

    # Stock or index assets, or unknown assets, default to TRY rate
    if not (is_currency or is_metal):
        return RATES.get('TRY', 0.0) 
        
    cur1 = asset_clean[:3]
    cur2 = asset_clean[3:6]
    
    rate1 = RATES.get(cur1, 0.0)
    rate2 = RATES.get(cur2, 0.0)
    
    if is_metal:
        if cur2 == 'TRY':
            usd_rate = RATES.get('USD', 0.0)
            try_rate = RATES.get('TRY', 0.0)
            return (1 + usd_rate) * (1 + try_rate) - 1
        else:
            return rate2
            
    if is_currency:
        return (1 + rate2) / (1 + rate1) - 1
        
    return RATES.get('TRY', 0.0)

def standardize_capital(df: pd.DataFrame) -> pd.DataFrame:
    # Only TRY and USD legs are considered as second legs.
    if df is None or df.empty:
        return df
        
    # Nearest USDTRY contract is used for FX rate determination
    usdtry_df = df[df['BaseAsset'] == 'USDTRY'].sort_values('Days')
    if not usdtry_df.empty:
        best_row = usdtry_df.iloc[0]
        base_usd_rate = best_row['bid'] if pd.notna(best_row['bid']) and best_row['bid'] > 0 else best_row['underlying_close']
    else:
        base_usd_rate = 1.0
        
    is_usd_leg = df['BaseAsset'].str.endswith('USD')
    df['FX_Rate'] = 1.0
    df.loc[is_usd_leg, 'FX_Rate'] = base_usd_rate
    
    df['Req_Capital'] = df['psr_close'].astype(float) * df['FX_Rate']
    
    return df

if __name__ == "__main__":
    test_assets = ['USDTRY', 'EURUSD','XAUTRY', 'XAUTRYM', 'XPTUSD']
    
    for asset in test_assets:
        target_rate = calculate_target_rate(asset)
        print(f"Asset: {asset}, Target Rate: {target_rate:.6f}")
import pandas as pd

from config import *


class SpotFutureEngine:
    def __init__(self, min_volume_tl=SPOT_MIN_VOLUME_TL, monthly_rate=MONTHLY_RISK_FREE_RATE, stopaj=STOPPAGE, commission_rate=COMMISSION_RATE):
        self.min_volume_tl = min_volume_tl
        self.monthly_rate = monthly_rate
        self.stopaj = stopaj
        self.commission_rate = commission_rate

    def process(self, df: pd.DataFrame | None) -> pd.DataFrame:
        if df is None or df.empty: 
            return pd.DataFrame()
            
        df = df.dropna(subset=['underlying_close', 'bid', 'volume_lot', 'Req_Capital']).copy()
        df = df[(df['underlying_close'] > 0) & (df['bid'] > 0)]
        
        is_usd = df['BaseAsset'].str.endswith('USD')
        fx_rate = df['USD_Rate'].where(is_usd, 1.0)
        
        df['Volume_TL'] = df['volume_lot'] * df['bid'] * df['Multiplier'] * fx_rate
        df = df[df['Volume_TL'] >= self.min_volume_tl].copy()
        
        if df.empty:
            return df
            
        df['Gross_Profit'] = (df['bid'] - df['underlying_close']) * df['Multiplier'] * fx_rate
        df['Total_Comm'] = self.commission_rate * (df['bid'] + df['underlying_close']) * df['Multiplier'] * fx_rate
        df['Net_Profit'] = df['Gross_Profit'] - df['Total_Comm']
        
        # VIOP margin requirement is disregarded
        df['Spot_Cost'] = df['underlying_close'] * df['Multiplier'] * fx_rate
        df['Req_Capital'] = df['Spot_Cost'] 
        
        alt_gross = df['Req_Capital'] * ((1 + self.monthly_rate) ** (df['Days'] / 30)) - df['Req_Capital']
        df['Alt_Net_Return'] = alt_gross * (1 - self.stopaj)
        
        # (1+monthly_rate)^(30/days) - 1 mechanism // each return was standardized on a monthly basis
        day_factor = 30 / df['Days']
        df['Opp_Monthly_%'] = ((1 + df['Alt_Net_Return'] / df['Req_Capital']) ** day_factor - 1) * 100
        df['Arb_Monthly_%'] = ((1 + df['Net_Profit'] / df['Req_Capital']) ** day_factor - 1) * 100
        df['Gross_Monthly_%'] = ((1 + df['Gross_Profit'] / df['Req_Capital']) ** day_factor - 1) * 100

        df['Spot_Price'] = df['underlying_close']
        df['Future_Price'] = df['bid']
        
        opportunities = df[df['Net_Profit'] > df['Alt_Net_Return']].copy()
        return opportunities.sort_values(by='Arb_Monthly_%', ascending=False)
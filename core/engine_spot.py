import pandas as pd

from config import *


class SpotFutureEngine:
    def __init__(self, min_volume_tl=SPOT_MIN_VOLUME_TL, stopaj=STOPPAGE, commission_rate=COMMISSION_RATE):
        self.min_volume_tl = min_volume_tl
        self.stopaj = stopaj
        self.commission_rate = commission_rate

    def process(self, df: pd.DataFrame | None) -> pd.DataFrame:
        if df is None or df.empty: 
            return pd.DataFrame()
            
        df = df.dropna(subset=['underlying_close', 'bid', 'volume_lot', 'Req_Capital']).copy()
        df = df[(df['underlying_close'] > 0) & (df['bid'] > 0)]

        
        
        df['Volume_TL'] = df['volume_lot'] * df['bid'] * df['Multiplier'] * df['FX_Rate']
        df = df[df['Volume_TL'] >= self.min_volume_tl].copy()
        
        if df.empty:
            return df
            
        df['Gross_Profit'] = (df['bid'] - df['underlying_close']) * df['Multiplier'] * df['FX_Rate']
        df['Total_Comm'] = self.commission_rate * (df['bid'] + df['underlying_close']) * df['Multiplier'] * df['FX_Rate']
        df['Net_Profit'] = df['Gross_Profit'] - df['Total_Comm']
        
        # VIOP margin requirement is disregarded
        df['Spot_Cost'] = df['underlying_close'] * df['Multiplier'] * df['FX_Rate']
        df['Req_Capital'] = df['Spot_Cost'] 
        
        alt_gross = df['Req_Capital'] * ((1 + df['Target_Rate']) ** (df['Days'] / 365)) - df['Req_Capital']
        df['Alt_Net_Return'] = alt_gross * (1 - self.stopaj)
        
        day_factor = 30 / df['Days']
        df['Opp_Monthly_%'] = ((1 + df['Alt_Net_Return'] / df['Req_Capital']) ** day_factor - 1) * 100
        df['Arb_Monthly_%'] = ((1 + df['Net_Profit'] / df['Req_Capital']) ** day_factor - 1) * 100
        df['Gross_Monthly_%'] = ((1 + df['Gross_Profit'] / df['Req_Capital']) ** day_factor - 1) * 100

        df['Spot_Price'] = df['underlying_close']
        df['Future_Price'] = df['bid']
        
        opportunities = df[df['Net_Profit'] > df['Alt_Net_Return']].copy()
        return opportunities.sort_values(by='Arb_Monthly_%', ascending=False)

if __name__ == "__main__":
    mock_data = pd.DataFrame([
        {
            'Contract': 'F_AKBNK1026',
            'BaseAsset': 'AKBNK',
            'Multiplier': 100,
            'underlying_close': 10.0,
            'bid': 11.0,
            'volume_lot': 1000,
            'Req_Capital': 100.0,
            'Target_Rate': 0.40,
            'FX_Rate': 1.0,
            'Days': 30
        }
    ])

    engine = SpotFutureEngine(min_volume_tl=0, stopaj=0.0, commission_rate=0.001)
    result = engine.process(mock_data)
    print(result[['Contract', 'Net_Profit', 'Alt_Net_Return', 'Arb_Monthly_%']].to_string(index=False))
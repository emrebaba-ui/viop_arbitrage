import pandas as pd
from curl_cffi import requests
from datetime import datetime
import calendar
import re

class ContractSpecifier:
    @staticmethod
    def get_multiplier(base_asset: str) -> int:
        currencies = {'USDTRY', 'EURTRY', 'EURUSD', 'GBPUSD', 'CNHTRY', 'RUBTRY'}
        indices = {'XU030', 'XLBNK', 'X10XB', 'XSD25'}
        
        if base_asset in currencies: return 1000
        elif base_asset in indices: return 10
        return 100

class YieldCalculator:
    @staticmethod
    def calculate_days_to_exp(contract_code: str, current_date: datetime) -> int:
        match = re.search(r'\d{4,6}$', contract_code)
        if not match: return 1
        mmyy = match.group()
        month = int(mmyy[-4:-2])
        year = int("20" + mmyy[-2:])
        _, last_day = calendar.monthrange(year, month)
        return max((datetime(year, month, last_day) - current_date).days, 1)

class FintablesDataFetcher:
    def __init__(self):
        self.url = "https://markets.fintables.com/barbar/server/?type=future"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Origin": "https://fintables.com",
            "Referer": "https://fintables.com/"
        }

    def fetch(self):
        response = requests.get(self.url, headers=self.headers, impersonate="chrome")
        if response.status_code != 200: return None
        data = response.json()
        return pd.DataFrame([
            {"Contract": code, **dict(zip(data["columns"], vals))}
            for code, vals in data["results"].items()
        ])

class ArbitrageEngine:
    def __init__(self, min_volume=1000, monthly_rate=0.03, stopaj=0.175, commission_rate=0.001):
        self.min_volume = min_volume
        self.monthly_rate = monthly_rate
        self.stopaj = stopaj
        self.commission_rate = commission_rate
        self.current_date = datetime.now()

    def process(self, df):
        if df is None or df.empty: return None
            
        df = df.dropna(subset=['underlying_close', 'bid', 'volume_lot'])
        volume = df['volume_lot'] * df['bid']
        df = df[(df['underlying_close'] > 0) & (volume >= self.min_volume)].copy()
        
        df['BaseAsset'] = df['Contract'].apply(lambda x: re.sub(r'^(?:TM_)?F_|\d{4,6}$', '', x))
        multipliers = df['BaseAsset'].apply(ContractSpecifier.get_multiplier)
        days_to_exp = df['Contract'].apply(lambda x: YieldCalculator.calculate_days_to_exp(x, self.current_date))
        
        # 1 kontrat bazında net değerler
        gross_profit = (df['bid'] - df['underlying_close']) * multipliers
        total_commission = self.commission_rate * (df['bid'] + df['underlying_close']) * multipliers
        net_profit = gross_profit - total_commission
        
        # Gerekli sermaye = Spot + Komisyon
        required_capital = (df['underlying_close'] * multipliers) + total_commission
        
        # Fırsat maliyeti (Bileşik mevduat / TLREF)
        alt_gross_return = required_capital * ((1 + self.monthly_rate) ** (days_to_exp / 30)) - required_capital
        alt_net_return = alt_gross_return * (1 - self.stopaj)
        
        # Eklenen Sütunlar
        df['Spot_Price'] = df['underlying_close']
        df['Future_Price'] = df['bid']
        df['Days'] = days_to_exp
        df['Req_Capital'] = required_capital
        df['Gross_Profit'] = gross_profit
        df['Net_Profit'] = net_profit
        df['Alt_Net_Return'] = alt_net_return
        
        # Basit 30 günlük getiri yüzdeleri (Net Kar * 30 / Gün)
        df['Opp_Monthly_%'] = (df['Alt_Net_Return'] / df['Req_Capital']) * 100 * (30 / df['Days'])
        df['Arb_Monthly_%'] = (df['Net_Profit'] / df['Req_Capital']) * 100 * (30 / df['Days'])
        df['Gross_Monthly_%'] = (df['Gross_Profit'] / df['Req_Capital']) * 100 * (30 / df['Days'])

        # Yalnızca arbitraj kârı fırsat maliyetini aşanları getir
        opportunities = df[df['Net_Profit'] > df['Alt_Net_Return']].copy()
        
        cols = [
            'Contract', 'Spot_Price', 'Future_Price', 'Days', 
            'Req_Capital', 'Gross_Profit', 'Net_Profit', 'Alt_Net_Return', 
            'Opp_Monthly_%', 'Arb_Monthly_%', 'Gross_Monthly_%'
        ]
        return opportunities[cols].sort_values(by='Gross_Monthly_%', ascending=False)

if __name__ == "__main__":
    raw_df = FintablesDataFetcher().fetch()
    engine = ArbitrageEngine(min_volume=10000) 
    results = engine.process(raw_df)
    
    if results is None or results.empty:
        print("Net kârı alternatif TLREF getirisini aşan rasyonel bir kontrat bulunamadı.")
    else:
        print(results.round(2).to_string(index=False))
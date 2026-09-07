import pandas as pd
from itertools import combinations
import re
from datetime import datetime
import calendar
from stock_future_arbitrage import *

# Mevcut stock-future_arbitrage.py dosyasındaki sınıflar (FintablesDataFetcher, ContractSpecifier, vb.) burada varsayılmıştır.

class FutureSpreadEngine:
    def __init__(self, min_volume=1000, commission_rate=0.001):
        self.min_volume = min_volume
        self.commission_rate = commission_rate
        self.current_date = datetime.now()

    def process(self, df):
        if df is None or df.empty: return None
            
        df = df.dropna(subset=['underlying_close', 'ask', 'volume_lot'])
        df['Volume'] = df['volume_lot'] * df['ask']
        df = df[(df['underlying_close'] > 0) & (df['Volume'] >= self.min_volume)].copy()
        
        df['BaseAsset'] = df['Contract'].apply(lambda x: re.sub(r'^(?:TM_)?F_|\d{4,6}$', '', x))
        df['Multiplier'] = df['BaseAsset'].apply(ContractSpecifier.get_multiplier)
        df['Days'] = df['Contract'].apply(lambda x: YieldCalculator.calculate_days_to_exp(x, self.current_date))
        
        # Zımni yıllık faiz oranı hesaplaması (Implied Annual Rate)
        df['Implied_Rate'] = ((df['ask'] / df['underlying_close']) - 1) * (365 / df['Days'])
        
        spread_opportunities = []
        
        # Aynı dayanak varlığa ait kontratları grupla ve ikili kombinasyonlar oluştur
        for asset, group in df.groupby('BaseAsset'):
            if len(group) < 2: continue
            
            # Vade gününe göre sırala (Yakın Vade -> Uzak Vade)
            group = group.sort_values('Days')
            contracts = group.to_dict('records')
            
            for c1, c2 in combinations(contracts, 2):
                rate_diff = c2['Implied_Rate'] - c1['Implied_Rate']
                if rate_diff == 0: continue
                
                # Her iki bacak (long/short) için ödenecek toplam komisyon
                total_commission = (c1['ask'] + c2['ask']) * c1['Multiplier'] * self.commission_rate
                
                # Teorik günlük getiri beklentisi (Spot * Oran Farkı / 365)
                daily_expected_return = (rate_diff / 365) * c1['underlying_close'] * c1['Multiplier']
                
                # Başabaş Noktası (Gün)
                days_to_breakeven = total_commission / daily_expected_return if daily_expected_return > 0 else float('inf')
                
                spread_opportunities.append({
                    'Asset': asset,
                    'Near_Contract': c1['Contract'],
                    'Near_Price' : c1['ask'],
                    'Near_Volume': c1['Volume'],
                    'Far_Contract': c2['Contract'],
                    'Far_Price': c2['ask'],
                    'Far_Volume': c2['Volume'],
                    'Near_Rate_%': c1['Implied_Rate'] * 100,
                    'Far_Rate_%': c2['Implied_Rate'] * 100,
                    'Rate_Diff_%': rate_diff * 100,
                    'Total_Comm': total_commission,
                    'Daily_Return': daily_expected_return,
                    'Breakeven_Days': days_to_breakeven
                })
                
        results_df = pd.DataFrame(spread_opportunities)
        if not results_df.empty:
            # En düşük başabaş gününe sahip olanları (en hızlı kâra geçenleri) öne al
            results_df = results_df.sort_values(by='Breakeven_Days', ascending=True)
            
        return results_df

if __name__ == "__main__":
    raw_df = FintablesDataFetcher().fetch()
    engine = FutureSpreadEngine(min_volume=5000) 
    results = engine.process(raw_df)
    
    if results is None or results.empty:
        print("Uygun spread fırsatı bulunamadı.")
    else:
        # Görünümü temizlemek adına sadece rasyonel başabaş noktalarını filtrele
        valid_results = results[results['Breakeven_Days'] < 60]
        cols = ['Asset', 'Near_Contract', 'Near_Price', 'Near_Volume', 'Far_Contract', 'Far_Price', 'Far_Volume', 'Rate_Diff_%', 'Total_Comm', 'Daily_Return', 'Breakeven_Days']
        print(valid_results[cols].round(2).to_string(index=False))
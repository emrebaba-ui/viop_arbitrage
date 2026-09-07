import pandas as pd
from bs4 import BeautifulSoup
import re
import yfinance as yf
from datetime import datetime
import calendar

class ViopDataFetcher:
    def parse_viop_html(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table', {'class': 'table table-hover table-striped'})
        if not table: return None

        data = []
        rows = table.find('tbody').find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 6:
                code = cols[0].text.strip()
                
                # regex to extract base asset
                base_asset = re.sub(r'^(?:TM_)?F_|\d{4,6}$', '', code)
                
                # extract MMYY from the end of the code
                mmyy = re.search(r'\d{4,6}$', code).group()
                if len(mmyy) >= 4:
                    month = int(mmyy[-4:-2])
                    year = int("20" + mmyy[-2:])
                    # VIOP contracts usually expire on the last business day of the month
                    _, last_day = calendar.monthrange(year, month)
                    exp_date = datetime(year, month, last_day)
                    days_to_exp = (exp_date - datetime.now()).days
                else:
                    days_to_exp = 0

                try:
                    price = float(cols[2].text.strip().replace(',', '.'))
                    bid = float(cols[4].text.strip().replace(',', '.'))
                    ask = float(cols[5].text.strip().replace(',', '.'))
                except ValueError:
                    price, bid, ask = 0.0, 0.0, 0.0

                data.append({
                    'Contract': code,
                    'BaseAsset': base_asset,
                    'DaysToExp': max(1, days_to_exp), # prevent division by zero
                    'LastPrice': price,
                    'Bid': bid,
                    'Ask': ask
                })
        
        df = pd.DataFrame(data)
        df = df[(df['Bid'] > 0) & (df['Ask'] > 0)].copy()
        return df

class YFinanceSpotFetcher:
    def get_spot_prices(self, base_assets):
        ticker_map = {}
        for asset in base_assets:
            if asset in ['USDTRY', 'EURTRY', 'EURUSD', 'GBPUSD', 'CNHTRY', 'RUBTRY']:
                ticker_map[asset] = f"{asset}=X"
            elif asset.startswith('X'): # Indices (e.g. XU030)
                ticker_map[asset] = f"{asset}.IS"
            else:
                ticker_map[asset] = f"{asset}.IS" # Standard stocks
        
        yf_tickers = list(ticker_map.values())
        print(f"Fetching spot prices for {len(yf_tickers)} assets...")
        
        # batch download for speed
        data = yf.download(yf_tickers, period="1d", progress=False)['Close']
        
        spot_prices = {}
        for asset, yf_ticker in ticker_map.items():
            try:
                # get the last available close price
                if isinstance(data, pd.DataFrame):
                    price = data[yf_ticker].iloc[-1]
                else:
                    price = data.iloc[-1]
                
                if pd.notna(price):
                    spot_prices[asset] = float(price)
            except Exception:
                pass # skip if ticker not found on Yahoo Finance
                
        return spot_prices

class ArbitrageAnalyzer:
    def __init__(self, fixed_commission_try=247.0):
        self.commission = fixed_commission_try

    def calculate(self, viop_df, spot_prices):
        viop_df['SpotPrice'] = viop_df['BaseAsset'].map(spot_prices)
        df = viop_df.dropna(subset=['SpotPrice']).copy()
        
        # calculate implied annualized return (simple interest)
        df['GrossReturn'] = (df['Bid'] / df['SpotPrice']) - 1
        df['AnnualizedYield_%'] = (df['GrossReturn'] * (365 / df['DaysToExp'])) * 100
        
        # Net profit assuming 1 lot (contract sizes vary, using absolute spread here as baseline)
        df['Spread'] = df['Bid'] - df['SpotPrice']
        
        return df.sort_values(by='AnnualizedYield_%', ascending=False)

if __name__ == "__main__":
    # 1. Fetch VIOP Data
    fetcher = ViopDataFetcher()
    with open('oyak_viop_page.html', 'r', encoding='utf-8') as f:
        df_viop = fetcher.parse_viop_html(f.read())
    
    # 2. Fetch Spot Prices
    unique_assets = df_viop['BaseAsset'].unique()
    spot_fetcher = YFinanceSpotFetcher()
    spot_prices = spot_fetcher.get_spot_prices(unique_assets)
    
    # 3. Analyze
    analyzer = ArbitrageAnalyzer()
    results = analyzer.calculate(df_viop, spot_prices)
    
    print("\n--- Top Arbitrage Opportunities (By Annualized Yield) ---")
    cols_to_print = ['Contract', 'DaysToExp', 'SpotPrice', 'Bid', 'Spread', 'AnnualizedYield_%']
    # .round(2) formats the output to 2 decimal places for readability
    print(results[cols_to_print].head(15).round(2).to_string(index=False))
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
ERROR_LOG_FILE_PATH = PROJECT_ROOT / 'data' / 'arbitrage_error.log'
ARB_DB_FILE_PATH = PROJECT_ROOT / 'data' / 'arbitrage_logs.db'
TRADES_PATH = PROJECT_ROOT / 'data' / 'trades.csv'
FINTABLES_PROFILE_PATH = PROJECT_ROOT / 'data' / 'fintables_profile'

URL = "https://markets.fintables.com/barbar/server/?type=future"
HEADERS = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Origin": "https://fintables.com",
            "Referer": "https://fintables.com/",
            "X-Requested-With": "fintables1789457642-PSHF6s5M_tzTR8BlYJWET4mnLAjKDhNzSBaLCqYyz9M",
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo0MjIzNywibGljZW5zZXMiOltdLCJkZXZpY2VfaWQiOiIzM2EyYTMwN2ViNjNmNDAwMTA3YTkyMDE5ZTY4MGE5MyJ9.XayeorvG57wdl1bAFIUFkA4B7nwLNaQfnQt8om6zq38"
        }

# --- INTERVALS ---
FREQUENCY = 300
BACKOFF_TIME = 10
BACKOFF_MAX_RETRIES = 5

# --- FILTERS ---
DISPLAY_MODE = 'ALL'
ASSET_FILTER = 'ALL'

# --- FINANCIALS ---
COMMISSION_RATE = 0.001
STOPPAGE = 0.175
SPOT_MIN_VOLUME_TL = 10000
SPREAD_MIN_VOLUME_TL = 10000
ANNUAL_RISK_FREE_RATE = 0.36
MONTHLY_RISK_FREE_RATE = (1 + ANNUAL_RISK_FREE_RATE) ** (1/12) - 1

# --- ASSET CLASSES ---
CURRENCIES = {'USDTRY', 'EURTRY', 'EURUSD', 'GBPUSD', 'CNHTRY', 'RUBTRY'}
INDICES = {'XU030', 'XLBNK', 'X10XB', 'XSD25', 'SASX10'}
METALS = {'XAUUSD', 'XAUTRY', 'XAUTRYM', 'XPTUSD', 'XPDUSD', 'XAGUSD', 'XAGTRY', 'XCUUSD'}

# --- RISK-FREE RATES ---
CUR_RATE_DICT = {
    'USD': 0.04,
    'EUR': 0.265,
    'GBP': 0.0375,
    'CNH': 0.03,
    'RUB': 0.14
}


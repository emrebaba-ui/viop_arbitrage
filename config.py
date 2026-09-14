from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
ERROR_LOG_FILE_PATH = PROJECT_ROOT / 'data' / 'arbitrage_error.log'
ARB_DB_FILE_PATH = PROJECT_ROOT / 'data' / 'arbitrage_logs.db'
TRADES_PATH = PROJECT_ROOT / 'data' / 'trades.csv'

# --- FILTERS ---
DISPLAY_MODE = 'ALL'
ASSET_FILTER = 'ALL'

# --- FINANCIALS ---
COMMISSION_RATE = 0.001
STOPPAGE = 0.175
SPOT_MIN_VOLUME_TL = 10000
SPREAD_MIN_VOLUME_TL = 10000
ANNUAL_RISK_FREE_RATE = 0.37
MONTHLY_RISK_FREE_RATE = (1 + ANNUAL_RISK_FREE_RATE) ** (1/12) - 1

# --- ASSET CLASSES ---
CURRENCIES = {'USDTRY', 'EURTRY', 'EURUSD', 'GBPUSD', 'CNHTRY', 'RUBTRY'}
INDICES = {'XU030', 'XLBNK', 'X10XB', 'XSD25', 'SASX10'}
METALS = {'XAUUSD', 'XAUTRY', 'XAUTRYM', 'XPTUSD', 'XPDUSD', 'XAGUSD', 'XAGTRY', 'XCUUSD'}


"""
 ** In case of a API key **
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
"""
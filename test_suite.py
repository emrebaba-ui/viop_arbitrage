import unittest
import pandas as pd
from datetime import datetime

from data import get_base_asset, get_multiplier
from engine_spot import SpotFutureEngine
from engine_spread import FutureSpreadEngine
from position_tracker import PositionTracker


class TestArbitrageModules(unittest.TestCase):
    
    def test_get_base_asset_parsing(self):
        self.assertEqual(get_base_asset('F_USDTRY0926'), 'USDTRY')
        self.assertEqual(get_base_asset('F_XU0301026'), 'XU030')
        self.assertEqual(get_base_asset('F_THYAO0926'), 'THYAO')
        self.assertEqual(get_base_asset('TM_F_XAGUSD1226'), 'XAGUSD')

    def test_multiplier_logic(self):
        self.assertEqual(get_multiplier('USDTRY'), 1000)
        self.assertEqual(get_multiplier('XU030'), 10)
        self.assertEqual(get_multiplier('XAUUSD'), 1)
        self.assertEqual(get_multiplier('XAGUSD'), 10)
        self.assertEqual(get_multiplier('THYAO'), 100)

    def test_engine_empty_dataframe_handling(self):
        spot_engine = SpotFutureEngine()
        spread_engine = FutureSpreadEngine()
        empty_df = pd.DataFrame()
        
        self.assertTrue(spot_engine.process(empty_df).empty)
        self.assertTrue(spread_engine.process(empty_df).empty)
        self.assertTrue(spot_engine.process(None).empty)
        self.assertTrue(spread_engine.process(None).empty)

    def test_position_tracker_string_parsing(self):
        tracker = PositionTracker('dummy.csv')
        action, contract, price = tracker.parse_action("SELL: F_HALKB0926 @ 50.92")
        
        self.assertEqual(action, "SELL")
        self.assertEqual(contract, "F_HALKB0926")
        self.assertEqual(price, 50.92)

    def test_spot_engine_math(self):
        mock_data = pd.DataFrame([{
            'Contract': 'F_AKBNK1026',
            'BaseAsset': 'AKBNK',
            'Multiplier': 100,
            'underlying_close': 10.0,
            'bid': 11.0,
            'volume_lot': 1000,
            'Req_Capital': 1000.0,
            'USD_Rate': 1.0,
            'Days': 30
        }])
        
        engine = SpotFutureEngine(min_volume_tl=0, monthly_rate=0.03, stopaj=0.175, commission_rate=0.001)
        result = engine.process(mock_data)
        
        self.assertFalse(result.empty, "Arbitrage opportunity was missed.")
        
        self.assertAlmostEqual(result.iloc[0]['Net_Profit'], 97.9, places=2)
        self.assertEqual(result.iloc[0]['Spot_Price'], 10.0)

    def test_spread_engine_math(self):
        mock_data = pd.DataFrame([
            {'Contract': 'F_AKBNK0926', 'BaseAsset': 'AKBNK', 'Multiplier': 100, 'bid': 10.0, 'ask': 10.1, 'volume_lot': 1000, 'Req_Capital': 1000, 'USD_Rate': 1.0, 'Days': 30},
            {'Contract': 'F_AKBNK1026', 'BaseAsset': 'AKBNK', 'Multiplier': 100, 'bid': 11.0, 'ask': 11.1, 'volume_lot': 1000, 'Req_Capital': 1000, 'USD_Rate': 1.0, 'Days': 60}
        ])
        
        engine = FutureSpreadEngine(target_rate=0.37, min_volume_tl=0, commission_rate=0.001)
        result = engine.process(mock_data)
        
        self.assertFalse(result.empty, "Arbitrage opportunity was missed.")
        
        expected_columns = ['Near_Action', 'Far_Action', 'Hold', 'Implied_%', 'Net_Profit', 'Pot_Profit']
        for col in expected_columns:
            self.assertIn(col, result.columns, f"{col} column is missing!")
            
        self.assertFalse(pd.isna(result.iloc[0]['Net_Profit']))
        self.assertTrue(result.iloc[0]['Net_Profit'] > 0)

from storage import StorageManager

class TestStorageManager(unittest.TestCase):
    def setUp(self):
        self.db = StorageManager(db_name=":memory:")
        
    def test_table_creation(self):
        self.db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='spread_logs'")
        self.assertIsNotNone(self.db.cursor.fetchone(), "spread_logs table could not be created!")

    def test_save_empty_dataframe(self):
        empty_df = pd.DataFrame()
        self.db.save(empty_df)
        self.db.cursor.execute("SELECT COUNT(*) FROM spread_logs")
        self.assertEqual(self.db.cursor.fetchone()[0], 0)

    def test_asset_filtering(self):
        mock_data = pd.DataFrame([
            {'Asset': 'XU030', 'Near_Action': 'BUY', 'Far_Action': 'SELL', 'Net_Profit': 100, 'Daily_Profit': 10, 'Req_Capital': 1000, 'Daily_ROI_%': 1},
            {'Asset': 'THYAO', 'Near_Action': 'BUY', 'Far_Action': 'SELL', 'Net_Profit': 50, 'Daily_Profit': 5, 'Req_Capital': 500, 'Daily_ROI_%': 1}, # Hisse, filtreye takılmalı
            {'Asset': 'USDTRY', 'Near_Action': 'SELL', 'Far_Action': 'BUY', 'Net_Profit': 200, 'Daily_Profit': 20, 'Req_Capital': 2000, 'Daily_ROI_%': 1}
        ])
        
        self.db.should_log = lambda: True 
        self.db.save(mock_data)
        
        self.db.cursor.execute("SELECT asset FROM spread_logs")
        saved_assets = [row[0] for row in self.db.cursor.fetchall()]
        
        self.assertIn('XU030', saved_assets)
        self.assertIn('USDTRY', saved_assets)
        self.assertNotIn('THYAO', saved_assets, "Critical Error: Stocks are leaking into the database!")

if __name__ == '__main__':
    unittest.main(verbosity=1)
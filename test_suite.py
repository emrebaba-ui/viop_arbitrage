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
            self.assertIn(col, result.columns, f"{col} sütunu eksik!")
            
        self.assertFalse(pd.isna(result.iloc[0]['Net_Profit']))
        self.assertTrue(result.iloc[0]['Net_Profit'] > 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
import sqlite3
import pandas as pd
from datetime import datetime

from config import *


class StorageManager:
    def __init__(self, db_name="arbitrage_logs.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS spread_logs (
                timestamp DATETIME,
                asset TEXT,
                near_action TEXT,
                far_action TEXT,
                net_profit REAL,
                daily_profit REAL,
                req_capital REAL,
                daily_ROI REAL
            )
        ''')
        self.conn.commit()

    def should_log(self) -> bool:
        now = datetime.now()

        if now.weekday() >= 5:
            return False
        
        if now.hour < 10 or now.hour > 18:
            return False

        self.cursor.execute("SELECT MAX(timestamp) FROM spread_logs")
        last_record = self.cursor.fetchone()[0]
        
        if last_record:
            last_log_time = datetime.strptime(last_record, "%Y-%m-%d %H:%M:%S")
            if (now - last_log_time).total_seconds() < 3600:
                return False
                
        return True

    def save(self, df: pd.DataFrame):
        if df is None or df.empty or not self.should_log():
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_classes = CURRENCIES | INDICES | METALS
        
        filtered_df = df[df['Asset'].isin(target_classes)]
        
        for _, row in filtered_df.iterrows():
            self.cursor.execute('''
                INSERT INTO spread_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (now_str, row['Asset'], row['Near_Action'], 
                  row['Far_Action'], row['Net_Profit'], row['Daily_Profit'], row['Req_Capital'], row['Daily_ROI_%']))
            
        self.conn.commit()
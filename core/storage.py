import sqlite3
from contextlib import closing
from datetime import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd

from config import *


class StorageManager:
    def __init__(self, db_name=ARB_DB_FILE_PATH):
        self.db_name = db_name
        self._create_table()

    def _connection(self):
        return sqlite3.connect(self.db_name)

    def _create_table(self):
        with closing(self._connection()) as conn:
            with conn:
                conn.execute("""
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
                """)

    def _should_log(self, conn) -> bool:
        now = dt.now(tz=ZoneInfo("Europe/Istanbul"))

        if now.weekday() >= 5 or now.hour < 10 or now.hour > 18:
            return False

        last_record = conn.execute(
            "SELECT MAX(timestamp) FROM spread_logs"
        ).fetchone()[0]

        if last_record:
            last_log_time = dt.strptime(
                last_record,
                "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=ZoneInfo("Europe/Istanbul"))

            if (now - last_log_time).total_seconds() < 3600:
                return False

        return True

    def should_log(self) -> bool:
        with closing(self._connection()) as conn:
            return self._should_log(conn)

    def save(self, df: pd.DataFrame):
        if df is None or df.empty:
            return

        target_classes = CURRENCIES | INDICES | METALS

        filtered_df = df.loc[
            df["Asset"].isin(target_classes),
            [
                "Asset",
                "Near_Action",
                "Far_Action",
                "Net_Profit",
                "Daily_Profit",
                "Req_Capital",
                "Daily_ROI_%",
            ],
        ]

        if filtered_df.empty:
            return

        now_str = dt.now().strftime("%Y-%m-%d %H:%M:%S")

        rows = (
            (
                now_str,
                asset,
                near_action,
                far_action,
                net_profit,
                daily_profit,
                req_capital,
                daily_roi,
            )
            for (
                asset,
                near_action,
                far_action,
                net_profit,
                daily_profit,
                req_capital,
                daily_roi,
            ) in filtered_df.itertuples(index=False, name=None)
        )

        with closing(self._connection()) as conn:
            with conn:
                if not self._should_log(conn):
                    return

                conn.executemany(
                    """
                    INSERT INTO spread_logs (
                        timestamp,
                        asset,
                        near_action,
                        far_action,
                        net_profit,
                        daily_profit,
                        req_capital,
                        daily_ROI
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
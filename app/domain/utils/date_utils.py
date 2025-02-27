"""
日時処理用ユーティリティ
"""
from datetime import datetime
from typing import Optional


class DateUtils:
    """日時処理に関するユーティリティクラス"""

    @staticmethod
    def parse_iso_date(date_str: str) -> Optional[datetime]:
        """
        ISO8601形式の日時文字列をdatetimeオブジェクトに変換する

        Args:
            date_str (str): ISO8601形式の日時文字列（例: 2024-04-01T12:34:56Z）

        Returns:
            Optional[datetime]: 変換されたdatetimeオブジェクト、変換失敗時はNone
        """
        try:
            # 'Z'をタイムゾーン表記'+00:00'に置換して解析
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            # 解析エラー時はNoneを返す
            return None

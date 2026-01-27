"""桜の開花状態判定サービス

都道府県別オフセット値に基づき、撮影日から8段階の開花状態を計算する。
Requirements: 1.1-1.13
"""

import csv
from dataclasses import dataclass
from datetime import date
from typing import Literal

from loguru import logger

from app.domain.services.flowering_date_service import get_flowering_date_service


# DB保存用の英語キー
BloomStatus = Literal[
    "before_bloom",
    "blooming",
    "30_percent",
    "50_percent",
    "full_bloom",
    "falling",
    "with_leaves",
    "leaves_only",
]

# UI表示用マッピング（フロントエンド・API レスポンスで使用）
BLOOM_STATUS_LABELS: dict[str, str] = {
    "before_bloom": "開花前",
    "blooming": "開花",
    "30_percent": "3分咲き",
    "50_percent": "5分咲き",
    "full_bloom": "8分咲き（満開）",
    "falling": "散り始め",
    "with_leaves": "花＋若葉（葉桜）",
    "leaves_only": "葉のみ",
}


@dataclass
class PrefectureOffsets:
    """都道府県別オフセット値"""

    flowering_to_3bu: int  # 開花→3分咲きオフセット（日）
    flowering_to_5bu: int  # 開花→5分咲きオフセット（日）
    end_to_hanawakaba: int  # 満開終了→花＋若葉オフセット（日）
    end_to_hanomi: int  # 満開終了→葉のみオフセット（日）


class BloomStateService:
    """桜の開花状態判定サービス"""

    def __init__(self) -> None:
        """260121_bloom_state.csv を読み込んで初期化"""
        self._prefecture_offsets: dict[str, PrefectureOffsets] = {}
        self._load_bloom_state_csv()

    def _parse_date_string(self, date_str: str, target_year: int) -> date | None:
        """日付文字列「M月D日」をパースする

        Args:
            date_str: "4月17日" 形式の日付文字列
            target_year: 年度

        Returns:
            date または None（パース失敗時）
        """
        if not date_str or date_str == "-":
            return None
        try:
            month_idx = date_str.find("月")
            day_idx = date_str.find("日")
            if month_idx < 0 or day_idx < 0:
                return None
            month = int(date_str[:month_idx])
            day = int(date_str[month_idx + 1:day_idx])
            return date(target_year, month, day)
        except (ValueError, IndexError) as e:
            logger.warning(f"日付パースエラー: {date_str}, {e}")
            return None

    def _load_bloom_state_csv(self) -> None:
        """260121_bloom_state.csv を読み込んでオフセット値を計算"""
        try:
            with open("master/260121_bloom_state.csv", "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                rows = list(reader)

                # ヘッダー行（1-2行目）と例示行（3行目）をスキップ
                # データ行は4行目（インデックス3）以降
                for row in rows[3:]:
                    if len(row) < 9:
                        continue

                    prefecture_code = row[0].strip()

                    # "例"行はスキップ
                    if prefecture_code == "例":
                        continue

                    # 沖縄県など、データがない場合（全て "-"）
                    if row[2].strip() == "-":
                        logger.debug(
                            f"都道府県コード {prefecture_code} はデータなし（スキップ）"
                        )
                        continue

                    try:
                        # 仮の年度（計算には影響しない）
                        base_year = 2025

                        # 各ステータスの開始日をパース
                        flowering_date = self._parse_date_string(
                            row[2].strip(), base_year
                        )
                        three_bu_date = self._parse_date_string(
                            row[3].strip(), base_year
                        )
                        five_bu_date = self._parse_date_string(
                            row[4].strip(), base_year
                        )
                        falling_date = self._parse_date_string(
                            row[6].strip(), base_year
                        )
                        hanawakaba_date = self._parse_date_string(
                            row[7].strip(), base_year
                        )
                        hanomi_date = self._parse_date_string(row[8].strip(), base_year)

                        if (
                            flowering_date is None
                            or three_bu_date is None
                            or five_bu_date is None
                            or falling_date is None
                            or hanawakaba_date is None
                            or hanomi_date is None
                        ):
                            logger.warning(
                                f"都道府県コード {prefecture_code} の日付データが不完全"
                            )
                            continue

                        # オフセット値を計算
                        flowering_to_3bu = (three_bu_date - flowering_date).days
                        flowering_to_5bu = (five_bu_date - flowering_date).days
                        # falling_date（散り始め）を基準に計算
                        end_to_hanawakaba = (hanawakaba_date - falling_date).days
                        end_to_hanomi = (hanomi_date - falling_date).days

                        self._prefecture_offsets[prefecture_code] = PrefectureOffsets(
                            flowering_to_3bu=flowering_to_3bu,
                            flowering_to_5bu=flowering_to_5bu,
                            end_to_hanawakaba=end_to_hanawakaba,
                            end_to_hanomi=end_to_hanomi,
                        )

                    except Exception as e:
                        logger.warning(
                            f"都道府県コード {prefecture_code} のオフセット計算エラー: {e}"
                        )
                        continue

                logger.info(
                    f"{len(self._prefecture_offsets)}件の都道府県別オフセットを読み込みました"
                )

        except FileNotFoundError:
            logger.error("260121_bloom_state.csv が見つかりません")
        except Exception as e:
            logger.error(f"260121_bloom_state.csv の読み込みエラー: {e}")

    def get_prefecture_offsets(
        self, prefecture_code: str
    ) -> PrefectureOffsets | None:
        """都道府県コードからオフセット値を取得

        Args:
            prefecture_code: 都道府県コード（"01"-"47"）

        Returns:
            PrefectureOffsets または None（データがない場合）
        """
        return self._prefecture_offsets.get(prefecture_code)

    def _get_flowering_dates(
        self, latitude: float, longitude: float, target_year: int
    ) -> tuple[date | None, date | None, date | None]:
        """開花予想日情報を取得

        Args:
            latitude: 緯度
            longitude: 経度
            target_year: 撮影年

        Returns:
            (開花予想日, 満開開始予想日, 満開終了予想日) のタプル
        """
        flowering_service = get_flowering_date_service()
        spot = flowering_service.find_nearest_spot(latitude, longitude)

        if not spot:
            return (None, None, None)

        try:
            flowering_date = spot.flowering_date.replace(year=target_year)
            full_bloom_start = spot.full_bloom_date.replace(year=target_year)
            full_bloom_end = spot.full_bloom_end_date.replace(year=target_year)
            return (flowering_date, full_bloom_start, full_bloom_end)
        except Exception as e:
            logger.warning(f"開花予想日の年度調整エラー: {e}")
            return (None, None, None)

    def calculate_bloom_status(
        self,
        photo_date: date,
        latitude: float,
        longitude: float,
        prefecture_code: str | None,
    ) -> BloomStatus | None:
        """開花状態を計算

        Args:
            photo_date: 撮影日
            latitude: 緯度
            longitude: 経度
            prefecture_code: 都道府県コード（Treeから取得）

        Returns:
            8段階の開花状態、または計算不能な場合 None
        """
        # 都道府県コードがない場合は計算不可
        if not prefecture_code:
            return None

        # 都道府県別オフセットを取得
        offsets = self.get_prefecture_offsets(prefecture_code)
        if not offsets:
            logger.debug(f"都道府県コード {prefecture_code} のオフセットがありません")
            return None

        # 開花予想日を取得
        flowering_date, full_bloom_start, full_bloom_end = self._get_flowering_dates(
            latitude, longitude, photo_date.year
        )

        if not flowering_date or not full_bloom_start:
            logger.debug("開花予想日が取得できません")
            return None

        # 満開終了日がない場合は満開開始+5日をデフォルトとする
        if not full_bloom_end:
            from datetime import timedelta

            full_bloom_end = full_bloom_start + timedelta(days=5)

        # 各ステータスの開始日を計算
        from datetime import timedelta

        # 開花日 = flowering_date
        # 3分咲き開始 = flowering_date + flowering_to_3bu
        three_bu_start = flowering_date + timedelta(days=offsets.flowering_to_3bu)
        # 5分咲き開始 = flowering_date + flowering_to_5bu
        five_bu_start = flowering_date + timedelta(days=offsets.flowering_to_5bu)
        # 満開開始 = full_bloom_start
        # 散り始め = full_bloom_end（満開終了予想日）
        # 花＋若葉開始 = full_bloom_end + end_to_hanawakaba
        hanawakaba_start = full_bloom_end + timedelta(days=offsets.end_to_hanawakaba)
        # 葉のみ開始 = full_bloom_end + end_to_hanomi
        hanomi_start = full_bloom_end + timedelta(days=offsets.end_to_hanomi)

        # ステータス判定
        if photo_date < flowering_date:
            return "before_bloom"
        elif photo_date < three_bu_start:
            return "blooming"
        elif photo_date < five_bu_start:
            return "30_percent"
        elif photo_date < full_bloom_start:
            return "50_percent"
        elif photo_date < full_bloom_end:
            return "full_bloom"
        elif photo_date < hanawakaba_start:
            return "falling"
        elif photo_date < hanomi_start:
            return "with_leaves"
        else:
            return "leaves_only"


# シングルトンパターンを実装
_bloom_state_service_instance: BloomStateService | None = None


def get_bloom_state_service() -> BloomStateService:
    """BloomStateService のシングルトンインスタンスを取得"""
    global _bloom_state_service_instance
    if _bloom_state_service_instance is None:
        _bloom_state_service_instance = BloomStateService()
    return _bloom_state_service_instance

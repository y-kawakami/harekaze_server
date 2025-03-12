from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass
class FloweringDateSpot:
    spot_id: str  # 地点番号
    prefecture: str  # 都道府県名
    address: str  # 住所
    latitude: float  # 緯度
    longitude: float  # 経度
    flowering_date: date  # 開花予想日
    full_bloom_date: date  # 満開予想日
    full_bloom_end_date: date  # 満開予想終了日
    variety: str  # 予想品種
    updated_date: date  # 更新日

    def _to_datetime(self, d: date) -> datetime:
        """dateをJSTのdatetimeに変換します（正午を基準とします）"""
        return datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))

    def _linear_interpolate(self, start_val: tuple[float, float], end_val: tuple[float, float], progress: float) -> tuple[float, float]:
        """2つの値の間を線形補間します。

        Args:
            start_val (tuple[float, float]): 開始時の値
            end_val (tuple[float, float]): 終了時の値
            progress (float): 進行度（0.0 ~ 1.0）

        Returns:
            tuple[float, float]: 補間された値
        """
        return (
            start_val[0] + (end_val[0] - start_val[0]) * progress,
            start_val[1] + (end_val[1] - start_val[1]) * progress
        )

    def estimate_vitality(self, target_date: datetime) -> tuple[float, float]:
        """指定された日時における桜の元気度を推定します。

        Args:
            target_date (datetime): 推定したい日時（タイムゾーン情報がない場合はUTCとして扱います）

        Returns:
            tuple[float, float]: (元気度推定A（花なし）, 元気度推定B（花あり）)のタプル
        """
        # target_dateのタイムゾーン処理
        if target_date.tzinfo is None:
            # タイムゾーンがない場合はUTCとして扱い、JSTに変換
            utc_dt = target_date.replace(tzinfo=ZoneInfo("UTC"))
            target_date = utc_dt.astimezone(ZoneInfo("Asia/Tokyo"))
        else:
            # タイムゾーン情報がある場合はJSTに変換
            target_date = target_date.astimezone(ZoneInfo("Asia/Tokyo"))

        # 日付をdatetimeに変換
        flowering_dt = self._to_datetime(self.flowering_date)
        full_bloom_dt = self._to_datetime(self.full_bloom_date)
        full_bloom_end_dt = self._to_datetime(self.full_bloom_end_date)
        leaf_dt = self._to_datetime(
            self.full_bloom_end_date + timedelta(days=5))

        # 各期間の時間差を計算（秒単位）
        time_to_flowering = (flowering_dt - target_date).total_seconds()
        time_to_full_bloom = (full_bloom_dt - target_date).total_seconds()
        time_to_end_bloom = (full_bloom_end_dt - target_date).total_seconds()
        time_to_leaf = (leaf_dt - target_date).total_seconds()

        # 開花前
        if time_to_flowering > 0:
            return (1.0, 0)

        # 開花～満開
        elif time_to_flowering <= 0 and time_to_full_bloom > 0:
            # 開花から満開までの進行度を計算
            total_bloom_time = (full_bloom_dt - flowering_dt).total_seconds()
            progress = 1.0 - (time_to_full_bloom / total_bloom_time)
            progress = max(0.0, min(1.0, progress))  # 0.0 ~ 1.0 に制限
            return self._linear_interpolate((1.0, 0), (0, 1.0), progress)

        # 満開
        elif time_to_full_bloom <= 0 and time_to_end_bloom > 0:
            return (0, 1.0)

        # 散り始め～葉桜
        elif time_to_end_bloom <= 0 and time_to_leaf > 0:
            # 散り始めから葉桜までの進行度を計算
            total_fall_time = (leaf_dt - full_bloom_end_dt).total_seconds()
            progress = 1.0 - (time_to_leaf / total_fall_time)
            progress = max(0.0, min(1.0, progress))  # 0.0 ~ 1.0 に制限
            return self._linear_interpolate((0.5, 0.5), (1.0, 0), progress)

        # 葉桜
        else:
            return (1.0, 0)

"""桜の開花日に関するサービス"""
import csv
from datetime import date, datetime
from typing import List, Optional

from loguru import logger

from app.domain.models.flowering_date_spot import FloweringDateSpot


class FloweringDateService:
    """桜の開花日取得のサービスクラス"""
    spots: List[FloweringDateSpot]

    def __init__(self):
        """
        開花日データを読み込んで初期化する
        """
        self._load_flowering_date_spots()

    def _load_flowering_date_spots(self):
        """開花日データをCSVファイルから読み込む"""
        try:
            with open('master/flowering_date.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.spots = []
                for row in reader:
                    try:
                        # 日付文字列を解析（例: "4月29日" → "2024-04-29"）
                        def parse_date(date_str: str) -> date:
                            month = int(date_str[0:date_str.find("月")])
                            day = int(date_str[date_str.find(
                                "月") + 1:date_str.find("日")])
                            # 現在の年を使用（本来は発表年度を使用すべき）
                            year = datetime.now().year
                            return date(year, month, day)

                        # 住所が都道府県名で始まる場合は都道府県名を除去
                        address = row['住所']
                        if address.startswith(row['都道府県']):
                            address = address[len(row['都道府県']):]

                        self.spots.append(
                            FloweringDateSpot(
                                spot_id=row['地点番号'],
                                prefecture=row['都道府県'],
                                address=row['都道府県'] + address,
                                latitude=float(row['緯度（10進法）']),
                                longitude=float(row['経度（10進法）']),
                                flowering_date=parse_date(row['開花予想日']),
                                full_bloom_date=parse_date(row['満開開始予想日']),
                                full_bloom_end_date=parse_date(row['満開終了予想日']),
                                variety=row['予想品種'].strip(),
                                updated_date=parse_date(row['発表日']),
                            )
                        )
                    except Exception as e:
                        logger.warning(f"データの解析に失敗しました: {str(e)}, row: {row}")
                        continue

                logger.info(f"{len(self.spots)}件の開花日データを読み込みました")
        except Exception as e:
            logger.error(f"開花日データの読み込みに失敗しました: {str(e)}")
            self.spots = []

    def _calculate_distance_sphere(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        2点間の距離をメートル単位で計算する（ST_Distance_Sphere相当）

        Args:
            lat1 (float): 地点1の緯度
            lon1 (float): 地点1の経度
            lat2 (float): 地点2の緯度
            lon2 (float): 地点2の経度

        Returns:
            float: 2点間の距離（メートル）
        """
        import math

        # 地球の半径（メートル）
        EARTH_RADIUS = 6371000

        # 緯度経度をラジアンに変換
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine公式による距離計算
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = math.sin(dlat / 2) * math.sin(dlat / 2) + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(dlon / 2) * math.sin(dlon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = EARTH_RADIUS * c

        return distance

    def find_nearest_spot(self, latitude: float, longitude: float) -> Optional[FloweringDateSpot]:
        """
        指定された緯度経度から最も近い開花予想地点を検索する

        Args:
            latitude (float): 緯度
            longitude (float): 経度

        Returns:
            Optional[FloweringDateSpot]: 最も近い開花予想地点
        """
        if not self.spots:
            return None

        nearest_spot = None
        min_distance = float('inf')

        for spot in self.spots:
            distance = self._calculate_distance_sphere(
                latitude, longitude, spot.latitude, spot.longitude)
            if distance < min_distance:
                nearest_spot = spot
                min_distance = distance
                # logger.debug(f"新しい最近接地点: {spot.address}（距離: {distance}m）")

        if nearest_spot:
            logger.debug(
                f"最終的な最近接地点: {nearest_spot.address}（距離: {min_distance}m）")

        return nearest_spot


# シングルトンパターンを実装
_flowering_date_service_instance = None


def get_flowering_date_service() -> FloweringDateService:
    """
    桜の開花日取得サービスを取得する
    一度だけインスタンスを生成し、以降は同じインスタンスを再利用します
    """
    global _flowering_date_service_instance
    if _flowering_date_service_instance is None:
        _flowering_date_service_instance = FloweringDateService()
    return _flowering_date_service_instance

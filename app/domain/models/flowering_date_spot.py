from dataclasses import dataclass
from datetime import date


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

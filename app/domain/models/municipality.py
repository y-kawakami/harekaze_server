from dataclasses import dataclass


@dataclass
class Municipality:
    code: str  # 団体コード
    name: str  # 団体名
    postal_code: str  # 新郵便番号
    address: str  # 住所
    phone: str  # 電話番号
    latitude: float  # 緯度
    longitude: float  # 経度

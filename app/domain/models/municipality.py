from dataclasses import dataclass


@dataclass
class Municipality:
    code: str  # 団体コード
    prefecture: str  # 都道府県名
    jititai: str  # 団体名
    city_kana: str  # 市区町村名（カナ）
    zip: str  # 新郵便番号
    address: str  # 住所
    tel: str  # 電話番号
    latitude: float  # 緯度
    longitude: float  # 経度

    def full_name(self) -> str:
        return self.prefecture + self.jititai

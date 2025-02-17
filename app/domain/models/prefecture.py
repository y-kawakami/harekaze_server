from dataclasses import dataclass


@dataclass
class Prefecture:
    """都道府県データクラス"""
    code: str
    name: str
    latitude: float
    longitude: float

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import googlemaps
from dotenv import load_dotenv
from loguru import logger

from app.domain.constants.prefecture import PREFECTURE_CODE_MAP
from app.domain.models.municipality import Municipality


@dataclass
class Address:
    """住所情報を表すデータクラス"""
    country: Optional[str]
    prefecture: Optional[str]
    prefecture_code: Optional[str]
    municipality: Optional[str]
    municipality_code: Optional[str]
    detail: Optional[str]  # 都道府県から始まる完全な住所


class GeocodingService:
    client: Any  # type: ignore
    municipalities: List[Municipality]
    municipality_by_code: Dict[str, Municipality]

    def __init__(self):
        """
        Google Maps Geocoding APIを使用して住所を取得するサービス
        """
        load_dotenv()
        api_key = os.getenv('GEOCODING_API_KEY')
        if not api_key:
            raise ValueError(
                "GEOCODING_API_KEY is not set in environment variables")
        self.client = googlemaps.Client(key=api_key)

        # 自治体データの読み込み
        self._load_municipalities()

    def _load_municipalities(self):
        """自治体データをJSONファイルから読み込む"""
        try:
            with open('master/municipalities.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.municipalities = [
                    Municipality(
                        code=item['code'],
                        name=item['name'],
                        postal_code=item['postal_code'],
                        address=item['address'],
                        phone=item['phone'],
                        latitude=item['latitude'],
                        longitude=item['longitude']
                    )
                    for item in data
                ]
                # コードでの高速検索用にディクショナリも作成
                self.municipality_by_code = {
                    m.code: m for m in self.municipalities
                }
                logger.info(f"{len(self.municipalities)}件の自治体データを読み込みました")
        except Exception as e:
            logger.error(f"自治体データの読み込みに失敗しました: {str(e)}")
            self.municipalities = []
            self.municipality_by_code = {}

    def _find_municipality(self, address: str) -> Optional[Municipality]:
        """
        住所から最適な自治体を特定する
        前方からの共通部分が最も長い自治体を返す

        Args:
            address (str): 完全な住所（例: 兵庫県神戸市東灘区2-3-1）

        Returns:
            Optional[Municipality]: マッチした自治体
        """
        if not address:
            return None

        # 最長一致の自治体を探す
        matched_municipality = None
        max_match_length = 0

        for municipality in self.municipalities:
            mun_address = municipality.address
            # 前方からの共通部分の長さを計算
            match_length = 0
            for i in range(min(len(address), len(mun_address))):
                if address[i] != mun_address[i]:
                    break
                match_length = i + 1

            # より長い一致が見つかった場合は更新
            if match_length > max_match_length:
                matched_municipality = municipality
                max_match_length = match_length
                logger.debug(f"新しい最長一致: {mun_address}（長さ: {match_length}）")

        if matched_municipality:
            logger.debug(
                f"最終的な一致: {matched_municipality.address}（長さ: {max_match_length}）")

        return matched_municipality

    def _get_prefecture_code(self, prefecture: str) -> Optional[str]:
        """
        都道府県名から都道府県コードを取得する

        Args:
            prefecture (str): 都道府県名

        Returns:
            Optional[str]: 都道府県コード
        """
        if not prefecture:
            return None

        # 都道府県名から「都」「府」「県」を除去
        prefecture = prefecture.replace(
            "都", "").replace("府", "").replace("県", "")

        # 定数マップから都道府県コードを取得
        return PREFECTURE_CODE_MAP.get(prefecture)

    def get_address(self, latitude: float, longitude: float) -> Address:
        """
        緯度経度から住所を取得する

        Args:
            latitude (float): 緯度
            longitude (float): 経度

        Returns:
            Address: 住所情報
        """
        try:
            result = self.client.reverse_geocode(
                (latitude, longitude), language='ja')

            if not result:
                logger.warning(f"住所が見つかりませんでした: ({latitude}, {longitude})")
                return Address(None, None, None, None, None, None)

            logger.debug(
                f"Geocoding API response: {json.dumps(result, indent=2, ensure_ascii=False)}")

            address_components = result[0]['address_components']
            prefecture = None
            municipality = None
            country = None
            address_parts = []

            # 都道府県と市区町村を抽出し、詳細住所を構築
            for component in address_components:
                comp_type = component['types'][0]
                if comp_type == 'country':
                    country = component['long_name']
                elif comp_type == 'administrative_area_level_1':
                    prefecture = component['long_name']
                    address_parts.append(component['long_name'])
                elif comp_type in ['locality', 'administrative_area_level_2']:
                    municipality = component['long_name']
                    address_parts.append(component['long_name'])
                # 詳細住所のコンポーネントを収集（郵便番号と国を除く）
                elif comp_type not in ['postal_code', 'country']:
                    address_parts.append(component['long_name'])

            # 詳細住所を構築（大きい区分から順に並べる）
            detailed_address = ''.join(
                reversed(address_parts)) if address_parts else None

            # 自治体の特定
            matched_municipality = self._find_municipality(
                detailed_address) if detailed_address else None
            municipality_code = matched_municipality.code if matched_municipality else None

            if matched_municipality and not municipality:
                municipality = matched_municipality.name

            # 都道府県コードを取得
            prefecture_code = self._get_prefecture_code(
                prefecture) if prefecture else None

            return Address(
                country=country,
                prefecture=prefecture,
                prefecture_code=prefecture_code,
                municipality=municipality,
                municipality_code=municipality_code,
                detail=detailed_address
            )

        except Exception as e:
            logger.error(f"Geocoding APIでエラーが発生しました: {str(e)}")
            return Address(None, None, None, None, None, None)


def get_geocoding_service() -> GeocodingService:
    return GeocodingService()


if __name__ == "__main__":
    # テスト用の実行例
    service = GeocodingService()

    # 大阪城の座標
    osaka_castle = (34.6873153, 135.5262013)
    print("\n大阪城のテスト:")
    address = service.get_address(*osaka_castle)
    print(f"国: {address.country}")
    print(f"都道府県: {address.prefecture}")
    print(f"市区町村: {address.municipality}")
    print(f"市区町村コード: {address.municipality_code}")
    print(f"詳細住所: {address.detail}")

    # 東京駅の座標
    tokyo_station = (35.6812362, 139.7671248)
    print("\n東京駅のテスト:")
    address = service.get_address(*tokyo_station)
    print(f"国: {address.country}")
    print(f"都道府県: {address.prefecture}")
    print(f"市区町村: {address.municipality}")
    print(f"市区町村コード: {address.municipality_code}")
    print(f"詳細住所: {address.detail}")

    # 馬路村
    umazato = (33.5554484, 134.0484039)
    print("\n馬路村のテスト:")
    address = service.get_address(*umazato)
    print(f"国: {address.country}")
    print(f"都道府県: {address.prefecture}")
    print(f"市区町村: {address.municipality}")
    print(f"市区町村コード: {address.municipality_code}")
    print(f"詳細住所: {address.detail}")

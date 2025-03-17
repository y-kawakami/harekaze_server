import json
import os
from dataclasses import dataclass
from typing import Any, Optional

import googlemaps
from dotenv import load_dotenv
from loguru import logger

from app.domain.services.municipality_service import MunicipalityService


@dataclass
class Address:
    """住所情報を表すデータクラス"""
    country: Optional[str]
    prefecture: Optional[str]
    prefecture_code: Optional[str]
    block: Optional[str]
    municipality: Optional[str]
    municipality_code: Optional[str]
    detail: Optional[str]  # 都道府県から始まる完全な住所


class GeocodingService:
    client: Any  # type: ignore
    municipality_service: MunicipalityService

    def __init__(self, municipality_service: MunicipalityService):
        """
        Google Maps Geocoding APIを使用して住所を取得するサービス

        Args:
            municipality_service (MunicipalityService): 自治体サービス
        """
        load_dotenv()
        api_key = os.getenv('GEOCODING_API_KEY')
        if not api_key:
            raise ValueError(
                "GEOCODING_API_KEY is not set in environment variables")
        self.client = googlemaps.Client(key=api_key)
        self.municipality_service = municipality_service

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
                return Address(None, None, None, None, None, None, None)

            logger.debug(
                f"Geocoding API response: {json.dumps(result, indent=2, ensure_ascii=False)}")

            address_components = result[0]['address_components']

            # plus_codeのみの結果の場合は住所なしとして扱う
            if len(address_components) == 1 and address_components[0]['types'][0] == 'plus_code':
                logger.warning(f"Plus Codeのみの結果でした: ({latitude}, {longitude})")
                return Address(None, None, None, None, None, None, None)

            prefecture = None
            municipality = None
            country = None
            address_parts = []

            # 都道府県と市区町村を抽出し、詳細住所を構築
            prefecture = None
            other_address_parts = []

            for component in address_components:
                comp_type = component['types'][0]
                if comp_type == 'country':
                    country = component['long_name']
                elif comp_type == 'administrative_area_level_1':
                    prefecture = component['long_name']
                elif comp_type in ['locality', 'administrative_area_level_2']:
                    municipality = component['long_name']
                    other_address_parts.append(component['long_name'])
                # 詳細住所のコンポーネントを収集（郵便番号と国を除く）
                elif comp_type not in ['postal_code', 'country']:
                    other_address_parts.append(component['long_name'])

            # 詳細住所を構築（都道府県を先頭に、その後に他の住所要素を逆順で追加）
            if prefecture:
                address_parts = [prefecture] + \
                    list(reversed(other_address_parts))
                detailed_address = ''.join(address_parts)
            else:
                detailed_address = ''.join(
                    reversed(other_address_parts)) if other_address_parts else None

            logger.debug(f'detailed_address = {detailed_address}')

            # 自治体の特定
            matched_municipality = self.municipality_service.find_municipality(
                detailed_address) if detailed_address else None
            municipality_code = matched_municipality.code if matched_municipality else None

            if matched_municipality and not municipality:
                municipality = matched_municipality.jititai

            # 都道府県コードを取得
            prefecture_code = None
            block = None
            if prefecture:
                prefecture_code = self.municipality_service.get_prefecture_code(
                    prefecture)
                if prefecture_code:
                    block = self.municipality_service.get_prefecture_block(
                        prefecture_code)

            return Address(
                country=country,
                prefecture=prefecture,
                prefecture_code=prefecture_code,
                block=block,
                municipality=municipality,
                municipality_code=municipality_code,
                detail=detailed_address
            )

        except Exception as e:
            logger.error(f"Geocoding APIでエラーが発生しました: {str(e)}")
            return Address(None, None, None, None, None, None, None)


def get_geocoding_service(municipality_service: MunicipalityService) -> GeocodingService:
    """GeocodingServiceのインスタンスを取得する"""
    return GeocodingService(municipality_service)

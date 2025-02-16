"""自治体関連のサービス"""
import json
from typing import Dict, List, Optional

from loguru import logger

from app.domain.constants.prefecture import PREFECTURE_CODE_MAP
from app.domain.models.municipality import Municipality


class MunicipalityService:
    """自治体関連のサービスクラス"""
    municipalities: List[Municipality]
    municipality_by_code: Dict[str, Municipality]

    def __init__(self):
        """
        自治体データを読み込んで初期化する
        """
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

    def find_municipality(self, address: str) -> Optional[Municipality]:
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

    def get_prefecture_code(self, prefecture: str) -> Optional[str]:
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


def get_municipality_service() -> MunicipalityService:
    """自治体関連のサービスを取得する"""
    return MunicipalityService()

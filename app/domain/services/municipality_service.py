"""自治体関連のサービス"""
import csv
from typing import Dict, List, Optional

from loguru import logger

from app.domain.constants.prefecture import PREFECTURE_CODE_MAP
from app.domain.models.municipality import Municipality
from app.domain.models.prefecture import Prefecture

# 都道府県ブロックの定義
PREFECTURE_BLOCK_MAP = {
    # ブロックA: 北海道・東北・関東
    "01": "A",  # 北海道
    "02": "A",  # 青森県
    "03": "A",  # 岩手県
    "04": "A",  # 宮城県
    "05": "A",  # 秋田県
    "06": "A",  # 山形県
    "07": "A",  # 福島県
    "08": "A",  # 茨城県
    "09": "A",  # 栃木県
    "10": "A",  # 群馬県
    "11": "A",  # 埼玉県
    "12": "A",  # 千葉県
    "13": "A",  # 東京都
    "14": "A",  # 神奈川県

    # ブロックB: 中部・近畿
    "15": "B",  # 新潟県
    "16": "B",  # 富山県
    "17": "B",  # 石川県
    "18": "B",  # 福井県
    "19": "B",  # 山梨県
    "20": "B",  # 長野県
    "21": "B",  # 岐阜県
    "22": "B",  # 静岡県
    "23": "B",  # 愛知県
    "24": "B",  # 三重県
    "25": "B",  # 滋賀県
    "26": "B",  # 京都府
    "27": "B",  # 大阪府
    "28": "B",  # 兵庫県
    "29": "B",  # 奈良県
    "30": "B",  # 和歌山県

    # ブロックC: 中国・四国・九州・沖縄
    "31": "C",  # 鳥取県
    "32": "C",  # 島根県
    "33": "C",  # 岡山県
    "34": "C",  # 広島県
    "35": "C",  # 山口県
    "36": "C",  # 徳島県
    "37": "C",  # 香川県
    "38": "C",  # 愛媛県
    "39": "C",  # 高知県
    "40": "C",  # 福岡県
    "41": "C",  # 佐賀県
    "42": "C",  # 長崎県
    "43": "C",  # 熊本県
    "44": "C",  # 大分県
    "45": "C",  # 宮崎県
    "46": "C",  # 鹿児島県
    "47": "C",  # 沖縄県
}


class MunicipalityService:
    """自治体関連のサービスクラス"""
    municipalities: List[Municipality]
    municipality_by_code: Dict[str, Municipality]
    prefectures: List[Prefecture]
    prefecture_by_name: Dict[str, Prefecture]
    prefecture_by_code: Dict[str, Prefecture]

    def __init__(self):
        """
        自治体データを読み込んで初期化する
        """
        self._load_municipalities()
        self._load_prefectures()

    def _load_municipalities(self):
        """自治体データをCSVファイルから読み込む"""
        try:
            with open('master/municipalities.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.municipalities = [
                    Municipality(
                        code=row['code'],
                        prefecture=row['prefecture'],
                        jititai=row['jititai'],
                        city_kana=row['city_kana'],
                        zip=row['zip'],
                        address=row['address'],
                        tel=row['tel'],
                        latitude=float(row['latitude']),
                        longitude=float(row['longitude'])
                    )
                    for row in reader
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

    def _load_prefectures(self):
        """都道府県データをCSVファイルから読み込む"""
        try:
            with open('master/pref_lat_lon.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.prefectures = []
                for row in reader:
                    # 都道府県名から都道府県コードを取得
                    pref_name = row['pref_name']
                    pref_code = self.get_prefecture_code(pref_name)
                    if pref_code:
                        self.prefectures.append(
                            Prefecture(
                                code=pref_code,
                                name=pref_name,
                                latitude=float(row['lat']),
                                longitude=float(row['lon'])
                            )
                        )
                # 都道府県名での高速検索用にディクショナリも作成
                self.prefecture_by_name = {
                    p.name: p for p in self.prefectures
                }
                self.prefecture_by_code = {
                    p.code: p for p in self.prefectures
                }
                logger.info(f"{len(self.prefectures)}件の都道府県データを読み込みました")
        except Exception as e:
            logger.error(f"都道府県データの読み込みに失敗しました: {str(e)}")
            self.prefectures = []
            self.prefecture_by_name = {}

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

        # 都道府県名から末尾の「都」「府」「県」を除去
        if prefecture.endswith("都") or prefecture.endswith("府") or prefecture.endswith("県"):
            prefecture = prefecture[:-1]

        # 定数マップから都道府県コードを取得
        return PREFECTURE_CODE_MAP.get(prefecture)

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

    def search_municipalities(self, latitude: float, longitude: float, radius: float) -> List[Municipality]:
        """
        指定された緯度経度から半径内の自治体を検索する

        Args:
            latitude (float): 緯度
            longitude (float): 経度
            radius (float): 検索半径（メートル）

        Returns:
            List[Municipality]: 検索された自治体のリスト
        """
        # 半径内の自治体を検索
        result = []
        for municipality in self.municipalities:
            distance = self._calculate_distance_sphere(
                latitude, longitude, municipality.latitude, municipality.longitude)
            if distance <= radius:
                result.append(municipality)
        return result

    def search_prefectures(self, latitude: float, longitude: float, radius: float) -> List[Prefecture]:
        """
        指定された緯度経度から半径内の都道府県を検索する

        Args:
            latitude (float): 緯度
            longitude (float): 経度
            radius (float): 検索半径（メートル）

        Returns:
            List[Prefecture]: 検索された都道府県のリスト
        """
        # 半径内の都道府県を検索
        result = []
        for prefecture in self.prefectures:
            distance = self._calculate_distance_sphere(
                latitude, longitude, prefecture.latitude, prefecture.longitude)
            if distance <= radius:
                result.append(prefecture)
        return result

    def get_municipality_by_code(self, code: str) -> Optional[Municipality]:
        """
        団体コードから自治体情報を取得する

        Args:
            code (str): 団体コード

        Returns:
            Optional[Municipality]: 取得した自治体情報
        """
        return self.municipality_by_code.get(code)

    def get_prefecture_by_code(self, code: str) -> Optional[Prefecture]:
        """
        都道府県コードから都道府県情報を取得する

        Args:
            code (str): 都道府県コード

        Returns:
            Optional[Prefecture]: 取得した都道府県情報
        """
        return self.prefecture_by_code.get(code)

    def get_prefecture_block(self, prefecture_code: str) -> Optional[str]:
        """
        都道府県コードからブロック（A, B, C）を取得する

        Args:
            prefecture_code: 都道府県コード

        Returns:
            Optional[str]: ブロック（A, B, C）
        """
        return PREFECTURE_BLOCK_MAP.get(prefecture_code)

    def get_prefectures_in_block(self, block: str) -> List[str]:
        """
        ブロック（A, B, C）に含まれる都道府県コードのリストを取得

        Args:
            block: ブロック（A, B, C）

        Returns:
            List[str]: 都道府県コードのリスト
        """
        return [code for code, b in PREFECTURE_BLOCK_MAP.items() if b == block]

    def find_municipality_codes_by_keyword(self, keyword: str) -> List[str]:
        """
        キーワードに一致する自治体のコードのリストを取得

        Args:
            keyword: 検索キーワード（自治体名の部分一致）

        Returns:
            List[str]: 自治体コードのリスト
        """
        if not keyword:
            return []

        matching_municipalities = []
        for muni in self.municipalities:
            name = muni.prefecture + muni.jititai
            if keyword in name:
                matching_municipalities.append(muni)

        return [muni.code for muni in matching_municipalities]


# シングルトンパターンを実装
_municipality_service_instance = None


def get_municipality_service() -> MunicipalityService:
    """
    自治体関連のサービスを取得する
    一度だけインスタンスを生成し、以降は同じインスタンスを再利用します
    """
    global _municipality_service_instance
    if _municipality_service_instance is None:
        _municipality_service_instance = MunicipalityService()
    return _municipality_service_instance

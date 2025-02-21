from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TreeBase(BaseModel):
    latitude: float = Field(..., description="緯度")
    longitude: float = Field(..., description="経度")


class TreeCreate(TreeBase):
    contributor: str = Field(..., description="投稿者名")


class TreeResponse(TreeBase):
    id: str = Field(..., description="登録した桜に付与されるID")
    tree_number: str = Field(..., description="表示用の番号（例: #23493）")
    contributor: Optional[str] = Field(None, description="投稿者名")
    vitality: Optional[int] = Field(None,
                                    description="元気度（1-5の整数値）", ge=1, le=5)
    latitude: float = Field(..., description="撮影場所の緯度")
    longitude: float = Field(..., description="撮影場所の経度")
    location: Optional[str] = Field(None, description="撮影場所（例: 東京都千代田区）")
    prefecture_code: Optional[str] = Field(
        None, description="都道府県コード（JIS X 0401に準拠）")
    municipality_code: Optional[str] = Field(
        None, description="自治体コード（JIS X 0402に準拠）")
    created_at: datetime = Field(..., description="撮影日時（ISO8601形式）")

    class Config:
        from_attributes = True


class TreeImageInfo(BaseModel):
    """画像情報の基底クラス"""
    image_url: str = Field(..., description="画像のURL")
    image_thumb_url: str = Field(..., description="サムネイル画像のURL")

    class Config:
        from_attributes = True


class StemInfo(TreeImageInfo):
    """幹の情報"""
    texture: Optional[int] = Field(
        None, description="幹の模様（1:滑らか~5:ガサガサ）", ge=1, le=5)
    can_detected: bool = Field(..., description="350ml缶の検出有無（樹齢推定に使用）")
    circumference: Optional[float] = Field(None, description="幹周（cm）（樹齢推定に使用）")
    age: Optional[int] = Field(None, description="推定樹齢（年）")
    created_at: datetime = Field(..., description="投稿日時")


class StemHoleInfo(TreeImageInfo):
    """幹の穴の情報"""
    created_at: datetime = Field(..., description="投稿日時")
    # severity: Optional[int] = Field(None, description="穴の深刻度（1-5）", ge=1, le=5)


class TengusuInfo(TreeImageInfo):
    """テングス病の情報"""
    created_at: datetime = Field(..., description="投稿日時")
    # severity: Optional[int] = Field(None, description="症状の深刻度（1-5）", ge=1, le=5)


class MushroomInfo(TreeImageInfo):
    """キノコの情報"""
    created_at: datetime = Field(..., description="投稿日時")
    # species: Optional[str] = Field(None, description="キノコの種類（判別できた場合）")
    # is_harmful: Optional[bool] = Field(None, description="有害なキノコかどうか")


class KobuInfo(TreeImageInfo):
    """こぶ状の枝の情報"""
    created_at: datetime = Field(..., description="投稿日時")


class TreeSearchFilter(BaseModel):
    vitality_min: Optional[int] = Field(
        None,
        description="元気度の最小値（1-5）",
        ge=1,
        le=5
    )
    vitality_max: Optional[int] = Field(
        None,
        description="元気度の最大値（1-5）",
        ge=1,
        le=5
    )
    age_min: Optional[int] = Field(None, description="樹齢の下限")
    age_max: Optional[int] = Field(None, description="樹齢の上限")
    has_hole: Optional[bool] = Field(
        None,
        description="幹に穴があるかどうか"
    )
    has_tengusu: Optional[bool] = Field(
        None,
        description="テングス病の有無"
    )
    has_mushroom: Optional[bool] = Field(
        None,
        description="キノコの有無"
    )


class TreeSearchRequest(BaseModel):
    latitude: float = Field(
        ...,
        description="検索の中心となる緯度"
    )
    longitude: float = Field(
        ...,
        description="検索の中心となる経度"
    )
    radius: float = Field(
        ...,
        description="検索半径（メートル）",
        gt=0
    )
    filter: Optional[TreeSearchFilter] = Field(
        None,
        description="検索フィルター条件"
    )
    page: int = Field(
        1,
        description="ページ番号",
        ge=1
    )
    per_page: int = Field(
        20,
        description="1ページあたりの表示件数",
        ge=1,
        le=100
    )


class TreeSearchResult(BaseModel):
    id: str = Field(..., description="桜のID")
    tree_number: str = Field(..., description="表示用の番号（例: #23493）")
    contributor: Optional[str] = Field(None, description="投稿者名")
    vitality: Optional[int] = Field(
        None, description="元気度（1-5の整数値）", ge=1, le=5)
    age: Optional[int] = Field(None, description="推定樹齢（年）")
    image_thumb_url: str = Field(..., description="サムネイル画像のURL")
    latitude: float = Field(..., description="緯度")
    longitude: float = Field(..., description="経度")
    location: Optional[str] = Field(None, description="撮影場所（例: 東京都千代田区）")
    prefecture_code: Optional[str] = Field(
        None, description="都道府県コード（JIS X 0401に準拠）")
    municipality_code: Optional[str] = Field(
        None, description="自治体コード（JIS X 0402に準拠）")
    created_at: datetime = Field(..., description="投稿日時")

    class Config:
        from_attributes = True


class TreeSearchResponse(BaseModel):
    total: int = Field(..., description="総ヒット件数")
    trees: List[TreeSearchResult] = Field(..., description="検索結果の桜の情報のリスト")


class TreeDetailResponse(TreeResponse):
    contributor: Optional[str] = Field(None, description="投稿者名")
    image_url: str = Field(..., description="桜の木全体の写真のURL")
    image_thumb_url: str = Field(..., description="桜の木全体の写真のサムネイルURL")
    decorated_image_url: Optional[str] = Field(..., description="装飾済み画像のURL")
    ogp_image_url: Optional[str] = Field(..., description="OGP画像のURL")
    stem: Optional[StemInfo] = Field(
        None, description="幹の情報（存在する場合のみ）")
    stem_hole: Optional[StemHoleInfo] = Field(
        None, description="幹の穴の情報（存在する場合のみ）")
    tengusu: Optional[TengusuInfo] = Field(
        None, description="テングス病の情報（存在する場合のみ）")
    mushroom: Optional[MushroomInfo] = Field(
        None, description="キノコの情報（存在する場合のみ）")
    kobu: Optional[KobuInfo] = Field(
        None, description="こぶ状の枝の情報（存在する場合のみ）")

    class Config:
        from_attributes = True


class TreeCountRequest(BaseModel):
    prefecture: Optional[str] = Field(None, description="都道府県")
    city: Optional[str] = Field(None, description="市区町村")
    filter: Optional[TreeSearchFilter] = Field(None, description="フィルタ条件")


class TreeCountResponse(BaseModel):
    count: int = Field(..., description="条件に合致する桜の本数")


class AreaCountItem(BaseModel):
    """エリア（都道府県または市区町村）ごとの集計情報"""
    prefecture_code: Optional[str] = Field(
        None, description="都道府県コード（JIS X 0401に準拠）")
    municipality_code: Optional[str] = Field(
        None, description="市区町村コード（JIS X 0402に準拠）")
    location: str = Field(..., description="都道府県名または市区町村名")
    count: int = Field(..., description="桜の本数")
    latitude: float = Field(..., description="エリアの中心緯度")
    longitude: float = Field(..., description="エリアの中心経度")
    # 最新の撮影者の情報
    latest_contributor: Optional[str] = Field(
        None, description="最新の撮影者のニックネーム")
    latest_image_thumb_url: Optional[str] = Field(
        None, description="最新の木のサムネイル画像のURL")


class AreaCountResponse(BaseModel):
    """エリアごとの桜の本数レスポンス"""
    total: int = Field(..., description="総本数")
    areas: List[AreaCountItem] = Field(..., description="エリアごとの集計結果")


class TreeStatsResponse(BaseModel):
    vitality_distribution: dict[int,
                                int] = Field(..., description="元気度の分布（キー: 1-5の元気度、値: 本数）")
    age_distribution: dict[str, int] = Field(
        ..., description="樹齢の分布（キー: 0-20/30-39/40-49/50-59/60+、値: 本数）")


class AreaStatsImage(BaseModel):
    """地域の統計情報の画像情報"""
    id: str = Field(..., description="登録した桜に付与されるID")
    image_url: str = Field(..., description="地域の統計情報の画像のURL")
    image_thumb_url: str = Field(..., description="地域の統計情報の画像のサムネイルURL")


class AreaStatsResponse(BaseModel):
    """地域の統計情報レスポンス"""
    total_trees: int = Field(..., description="桜の総本数")
    location: str = Field(..., description="地域名（都道府県名または市区町村名）")
    # 元気度の分布
    vitality1_count: int = Field(..., description="元気度1の木の本数")
    vitality2_count: int = Field(..., description="元気度2の木の本数")
    vitality3_count: int = Field(..., description="元気度3の木の本数")
    vitality4_count: int = Field(..., description="元気度4の木の本数")
    vitality5_count: int = Field(..., description="元気度5の木の本数")
    # 樹齢の分布
    age20_count: int = Field(..., description="樹齢0-20年の木の本数")
    age30_count: int = Field(..., description="樹齢30-39年の木の本数")
    age40_count: int = Field(..., description="樹齢40-49年の木の本数")
    age50_count: int = Field(..., description="樹齢50-59年の木の本数")
    age60_count: int = Field(..., description="樹齢60年以上の木の本数")
    # 問題の分布
    hole_count: int = Field(..., description="幹の穴がある木の本数")
    tengusu_count: int = Field(..., description="テングス病の木の本数")
    mushroom_count: int = Field(..., description="キノコが生えている木の本数")
    kobu_count: int = Field(..., description="こぶ状の枝がある木の本数")
    # 位置情報
    latitude: float = Field(..., description="地域の中心緯度")
    longitude: float = Field(..., description="地域の中心経度")
    # 画像情報
    hole_images: List[AreaStatsImage] = Field(
        ..., description="幹の穴の画像情報のリスト(最大30件)")
    tengusu_images: List[AreaStatsImage] = Field(
        ..., description="テングス病の画像情報のリスト(最大30件)")
    mushroom_images: List[AreaStatsImage] = Field(
        ..., description="キノコの画像情報のリスト(最大30件)")
    kobu_images: List[AreaStatsImage] = Field(
        ..., description="こぶ状の枝の画像情報のリスト(最大30件)")

    @classmethod
    def get_default(cls) -> "AreaStatsResponse":
        """デフォルト値を設定したインスタンスを返す"""
        return cls(
            total_trees=0,
            location="",
            vitality1_count=0,
            vitality2_count=0,
            vitality3_count=0,
            vitality4_count=0,
            vitality5_count=0,
            age20_count=0,
            age30_count=0,
            age40_count=0,
            age50_count=0,
            age60_count=0,
            hole_count=0,
            tengusu_count=0,
            mushroom_count=0,
            kobu_count=0,
            latitude=0.0,
            longitude=0.0,
            hole_images=[],
            tengusu_images=[],
            mushroom_images=[],
            kobu_images=[]
        )


class TreeDecoratedResponse(BaseModel):
    decorated_image_url: str = Field(..., description="装飾済み画像のURL")
    ogp_image_url: str = Field(..., description="OGP画像のURL")


class FloweringDateResponse(BaseModel):
    address: str = Field(..., description="住所（例: 東京都千代田区）")
    flowering_date: str = Field(..., description="開花予想日（例: 2024-03-20）")
    full_bloom_date: str = Field(..., description="満開予想日（例: 2024-03-27）")
    full_bloom_end_date: str = Field(..., description="満開予想終了日（例: 2024-04-03）")
    variety: str = Field(..., description="品種名（例: ソメイヨシノ）")

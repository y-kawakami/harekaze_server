from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.interfaces.schemas.stem import StemResponse as StemResponseSchema


class TreeBase(BaseModel):
    latitude: float = Field(..., description="緯度")
    longitude: float = Field(..., description="経度")


class TreeCreate(TreeBase):
    contributor: str = Field(..., description="投稿者名")


class TreeResponse(TreeBase):
    id: str = Field(..., description="登録した桜に付与されるID")
    tree_number: str = Field(..., description="表示用の番号（例: #23493）")
    vitality: int = Field(..., description="元気度（1-5の整数値）", ge=1, le=5)
    location: str = Field(..., description="撮影場所（例: 東京都千代田区）")
    created_at: datetime = Field(..., description="撮影日時（ISO8601形式）")

    class Config:
        from_attributes = True


class StemBase(BaseModel):
    latitude: float = Field(..., description="緯度")
    longitude: float = Field(..., description="経度")


class StemResponse(BaseModel):
    texture: int = Field(..., description="幹の模様（1:滑らか~5:ガサガサ）", ge=1, le=5)
    can_detected: bool = Field(..., description="350ml缶の検出有無（樹齢推定に使用）")
    circumference: Optional[float] = Field(None, description="幹周（cm）（樹齢推定に使用）")
    age: int = Field(..., description="推定樹齢（年）")

    class Config:
        from_attributes = True


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
    thumb_url: str = Field(..., description="サムネイル画像のURL")
    municipality: Optional[str] = Field(None, description="自治体名（例: 千代田区）")
    prefecture_code: Optional[str] = Field(
        None, description="都道府県コード（JIS X 0401に準拠）")
    municipality_code: Optional[str] = Field(
        None, description="自治体コード（JIS X 0402に準拠）")

    class Config:
        from_attributes = True


class TreeSearchResponse(BaseModel):
    total: int = Field(..., description="総ヒット件数")
    trees: List[TreeSearchResult] = Field(..., description="検索結果の桜の情報のリスト")


class TreeDetailResponse(TreeResponse):
    contributor: Optional[str] = Field(None, description="投稿者名")
    image_url: str = Field(..., description="桜の木全体の写真のURL")
    municipality: Optional[str] = Field(None, description="自治体名（例: 千代田区）")
    prefecture_code: Optional[str] = Field(
        None, description="都道府県コード（JIS X 0401に準拠）")
    municipality_code: Optional[str] = Field(
        None, description="自治体コード（JIS X 0402に準拠）")
    stem: Optional[StemResponseSchema] = Field(
        None, description="幹の情報（存在する場合のみ）")
    stem_hole_image_url: Optional[str] = Field(
        None, description="幹の穴の写真のURL（存在する場合のみ）")
    tengusu_image_url: Optional[str] = Field(
        None, description="テングス病の写真のURL（存在する場合のみ）")
    mushroom_image_url: Optional[str] = Field(
        None, description="キノコの写真のURL（存在する場合のみ）")

    class Config:
        from_attributes = True


class TreeCountRequest(BaseModel):
    prefecture: Optional[str] = Field(None, description="都道府県")
    city: Optional[str] = Field(None, description="市区町村")
    filter: Optional[TreeSearchFilter] = Field(None, description="フィルタ条件")


class TreeCountResponse(BaseModel):
    count: int = Field(..., description="条件に合致する桜の本数")


class TreeStatsResponse(BaseModel):
    vitality_distribution: dict[int,
                                int] = Field(..., description="元気度の分布（キー: 1-5の元気度、値: 本数）")
    age_distribution: dict[str, int] = Field(
        ..., description="樹齢の分布（キー: 0-20/30-39/40-49/50-59/60+、値: 本数）")


class FloweringDateResponse(BaseModel):
    address: str = Field(..., description="住所（例: 東京都千代田区）")
    flowering_date: str = Field(..., description="開花予想日（例: 2024-03-20）")
    full_bloom_date: str = Field(..., description="満開予想日（例: 2024-03-27）")

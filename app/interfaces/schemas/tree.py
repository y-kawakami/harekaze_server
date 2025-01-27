from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TreeBase(BaseModel):
    latitude: float = Field(..., description="緯度")
    longitude: float = Field(..., description="経度")


class TreeCreate(TreeBase):
    contributor_name: str = Field(..., description="投稿者名")


class TreeResponse(TreeBase):
    id: str = Field(..., description="Tree ID")
    tree_number: str = Field(..., description="表示用の番号")
    contributor: str = Field(..., description="投稿者名")
    vitality: int = Field(..., description="元気度（1-5の整数値）")
    location: str = Field(..., description="撮影場所")
    created_at: datetime = Field(..., description="撮影日時")

    class Config:
        from_attributes = True


class StemBase(BaseModel):
    latitude: float = Field(..., description="緯度")
    longitude: float = Field(..., description="経度")


class StemResponse(BaseModel):
    texture: int = Field(..., description="幹の模様（1:滑らか~5:ガサガサ）")
    can_detected: bool = Field(..., description="350ml缶の検出有無")
    circumference: Optional[float] = Field(None, description="幹周（cm）")
    age: int = Field(..., description="推定樹齢")

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
    id: str
    tree_number: str
    contributor_name: str
    thumb_url: str

    class Config:
        from_attributes = True


class TreeSearchResponse(BaseModel):
    total: int = Field(..., description="総ヒット件数")
    trees: List[TreeSearchResult] = Field(..., description="検索結果")


class TreeDetailResponse(TreeResponse):
    contributor: str
    image_url: str
    stem: Optional[StemResponse] = None
    stem_hole_image_url: Optional[str] = None
    tengusu_image_url: Optional[str] = None
    mushroom_image_url: Optional[str] = None

    class Config:
        from_attributes = True


class TreeCountRequest(BaseModel):
    prefecture: Optional[str] = Field(None, description="都道府県")
    city: Optional[str] = Field(None, description="市区町村")
    filter: Optional[TreeSearchFilter] = Field(None, description="フィルタ条件")


class TreeCountResponse(BaseModel):
    count: int = Field(..., description="桜の本数")


class TreeStatsResponse(BaseModel):
    vitality_distribution: dict[int, int] = Field(..., description="元気度の分布")
    age_distribution: dict[str, int] = Field(..., description="樹齢の分布")


class FloweringDateResponse(BaseModel):
    address: str = Field(..., description="住所")
    flowering_date: str = Field(..., description="開花予想日")
    full_bloom_date: str = Field(..., description="満開予想日")

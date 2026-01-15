"""アノテーションAPIのPydanticスキーマ定義

Requirements: 4.2
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class AnnotatorToken(BaseModel):
    """アノテーター認証トークンレスポンス"""
    access_token: str = Field(..., description="JWTアクセストークン")
    token_type: str = Field("bearer", description="トークンタイプ")


class AnnotatorResponse(BaseModel):
    """アノテーター情報レスポンス"""
    id: int = Field(..., description="アノテーターID")
    username: str = Field(..., description="アノテーターユーザー名")
    role: str = Field(..., description="アノテーターのロール（admin/annotator）")
    last_login: Optional[datetime] = Field(None, description="最終ログイン日時")
    created_at: datetime = Field(..., description="作成日時")

    class Config:
        from_attributes = True


class AnnotationRequest(BaseModel):
    """アノテーション保存リクエスト"""
    vitality_value: int = Field(
        ..., description="元気度（1-5）または診断不可（-1）")

    @field_validator("vitality_value")
    @classmethod
    def validate_vitality_value(cls, v: int) -> int:
        if v not in {-1, 1, 2, 3, 4, 5}:
            raise ValueError("vitality_value must be -1 or 1-5")
        return v


class AnnotationListItemResponse(BaseModel):
    """一覧アイテムレスポンス"""
    entire_tree_id: int = Field(..., description="EntireTree ID")
    tree_id: int = Field(..., description="Tree ID")
    thumb_url: str = Field(..., description="サムネイルURL")
    prefecture_name: str = Field(..., description="都道府県名")
    location: str = Field(..., description="撮影場所")
    annotation_status: Literal["annotated", "unannotated"] = Field(
        ..., description="アノテーション状態")
    vitality_value: Optional[int] = Field(None, description="元気度（1-5または-1）")


class AnnotationStatsResponse(BaseModel):
    """統計情報レスポンス"""
    total_count: int = Field(..., description="全件数")
    annotated_count: int = Field(..., description="アノテーション済み件数")
    unannotated_count: int = Field(..., description="未入力件数")
    vitality_1_count: int = Field(..., description="元気度1の件数")
    vitality_2_count: int = Field(..., description="元気度2の件数")
    vitality_3_count: int = Field(..., description="元気度3の件数")
    vitality_4_count: int = Field(..., description="元気度4の件数")
    vitality_5_count: int = Field(..., description="元気度5の件数")
    vitality_minus1_count: int = Field(..., description="診断不可の件数")


class AnnotationListResponse(BaseModel):
    """一覧レスポンス"""
    items: list[AnnotationListItemResponse] = Field(
        ..., description="一覧アイテム")
    stats: AnnotationStatsResponse = Field(..., description="統計情報")
    total: int = Field(..., description="フィルター適用後の総件数")
    page: int = Field(..., description="現在のページ番号")
    per_page: int = Field(..., description="1ページあたりの件数")


class AnnotationDetailResponse(BaseModel):
    """詳細レスポンス"""
    entire_tree_id: int = Field(..., description="EntireTree ID")
    tree_id: int = Field(..., description="Tree ID")
    image_url: str = Field(..., description="画像URL")
    photo_date: Optional[datetime] = Field(None, description="撮影日")
    prefecture_name: str = Field(..., description="都道府県名")
    location: str = Field(..., description="撮影場所")
    flowering_date: Optional[str] = Field(None, description="開花予想日")
    full_bloom_start_date: Optional[str] = Field(
        None, description="満開開始予想日")
    full_bloom_end_date: Optional[str] = Field(None, description="満開終了予想日")
    current_vitality_value: Optional[int] = Field(
        None, description="現在の元気度（1-5または-1）")
    current_index: int = Field(..., description="現在の位置（0-indexed）")
    total_count: int = Field(..., description="フィルター条件内の総件数")
    prev_id: Optional[int] = Field(None, description="前の画像ID")
    next_id: Optional[int] = Field(None, description="次の画像ID")


class SaveAnnotationResponse(BaseModel):
    """アノテーション保存レスポンス"""
    entire_tree_id: int = Field(..., description="EntireTree ID")
    vitality_value: int = Field(..., description="元気度")
    annotated_at: datetime = Field(..., description="アノテーション日時")
    annotator_id: int = Field(..., description="アノテーターID")


class PrefectureResponse(BaseModel):
    """都道府県レスポンス"""
    code: str = Field(..., description="都道府県コード")
    name: str = Field(..., description="都道府県名")


class PrefectureListResponse(BaseModel):
    """都道府県一覧レスポンス"""
    prefectures: list[PrefectureResponse] = Field(..., description="都道府県一覧")


class UpdateIsReadyRequest(BaseModel):
    """is_ready更新リクエスト"""
    is_ready: bool = Field(..., description="評価準備完了フラグ")


class UpdateIsReadyResponse(BaseModel):
    """is_ready更新レスポンス"""
    entire_tree_id: int = Field(..., description="EntireTree ID")
    is_ready: bool = Field(..., description="更新後のis_readyフラグ")
    updated_at: datetime = Field(..., description="更新日時")

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AdminLogin(BaseModel):
    """管理者ログインリクエスト"""
    username: str = Field(..., description="管理者ユーザー名")
    password: str = Field(..., description="管理者パスワード")


class AdminToken(BaseModel):
    """管理者認証トークンレスポンス"""
    access_token: str = Field(..., description="JWTアクセストークン")
    token_type: str = Field("bearer", description="トークンタイプ")


class AdminResponse(BaseModel):
    """管理者情報レスポンス"""
    id: int = Field(..., description="管理者ID")
    username: str = Field(..., description="管理者ユーザー名")
    last_login: Optional[datetime] = Field(None, description="最終ログイン日時")
    created_at: datetime = Field(..., description="作成日時")

    class Config:
        from_attributes = True


class AdminCreate(BaseModel):
    """管理者作成リクエスト"""
    username: str = Field(..., description="管理者ユーザー名")
    password: str = Field(..., description="管理者パスワード", min_length=8)


class AdminUpdate(BaseModel):
    """管理者更新リクエスト"""
    password: Optional[str] = Field(None, description="管理者パスワード", min_length=8)


class ImageCensorInfo(BaseModel):
    """画像の検閲情報"""
    image_thumb_url: Optional[str] = Field(None, description="サムネイル画像のURL")
    censorship_status: int = Field(...,
                                   description="検閲ステータス（0:未検閲, 1:OK, 2:NG, 3:エスカレーション）")


class TreeCensorItem(BaseModel):
    """検閲対象の投稿情報"""
    tree_id: int = Field(..., description="投稿ID")
    entire_tree: Optional[ImageCensorInfo] = Field(None, description="桜の全体画像")
    stem: Optional[ImageCensorInfo] = Field(None, description="幹の画像")
    stem_hole: Optional[ImageCensorInfo] = Field(None, description="幹の穴の画像")
    mushroom: Optional[ImageCensorInfo] = Field(None, description="キノコの画像")
    tengusu: Optional[ImageCensorInfo] = Field(None, description="テングス病の画像")
    kobu: Optional[ImageCensorInfo] = Field(None, description="こぶの画像")
    contributor: Optional[str] = Field(None, description="投稿者名")
    contributor_censorship_status: int = Field(..., description="投稿者名の検閲ステータス")
    location: Optional[str] = Field(None, description="撮影場所")
    latitude: float = Field(..., description="緯度")
    longitude: float = Field(..., description="経度")
    censorship_status: int = Field(..., description="投稿全体の検閲ステータス")
    created_at: datetime = Field(..., description="投稿日時")

    class Config:
        from_attributes = True


class TreeCensorListResponse(BaseModel):
    """投稿一覧レスポンス"""
    total: int = Field(..., description="総件数")
    items: List[TreeCensorItem] = Field(..., description="投稿一覧")


class TreeCensorListRequest(BaseModel):
    """投稿一覧リクエスト"""
    begin_date: Optional[datetime] = Field(None, description="検索開始日時")
    end_date: Optional[datetime] = Field(None, description="検索終了日時")
    municipality: Optional[str] = Field(None, description="自治体名（部分一致で検索）")
    tree_censorship_status: Optional[List[int]] = Field(
        None, description="全体の検閲ステータスリスト")
    detail_censorship_status: Optional[List[int]] = Field(
        None, description="詳細の検閲ステータスリスト")
    page: int = Field(1, description="ページ番号", ge=1)
    per_page: int = Field(20, description="1ページあたりの件数", ge=1, le=100)


class TreeCensorDetailResponse(TreeCensorItem):
    """検閲対象の投稿詳細情報"""
    censorship_ng_reason: Optional[str] = Field(None, description="NG理由")

    class Config:
        from_attributes = True


class CensorshipUpdateRequest(BaseModel):
    """検閲状態更新リクエスト"""
    tree_censorship_status: Optional[int] = Field(
        None, description="投稿全体の検閲ステータス")
    contributor_censorship_status: Optional[int] = Field(
        None, description="投稿者名の検閲ステータス")
    entire_tree_censorship_status: Optional[int] = Field(
        None, description="桜全体画像の検閲ステータス")
    stem_censorship_status: Optional[int] = Field(
        None, description="幹の検閲ステータス")
    stem_hole_censorship_status: Optional[int] = Field(
        None, description="幹の穴の検閲ステータス")
    mushroom_censorship_status: Optional[int] = Field(
        None, description="キノコの検閲ステータス")
    tengusu_censorship_status: Optional[int] = Field(
        None, description="テングス病の検閲ステータス")
    kobu_censorship_status: Optional[int] = Field(
        None, description="こぶの検閲ステータス")
    censorship_ng_reason: Optional[str] = Field(None, description="NG理由")


class DailyCensorshipStat(BaseModel):
    """日別検閲統計情報"""
    date: str = Field(..., description="日付（YYYY-MM-DD形式）")
    total_posts: int = Field(..., description="投稿総数")
    approved_count: int = Field(..., description="承認済み数")
    rejected_count: int = Field(..., description="拒否数")
    escalated_count: int = Field(..., description="エスカレーション数")
    uncensored_count: int = Field(..., description="未検閲数")


class CensorshipSummaryResponse(BaseModel):
    """検閲サマリーレスポンス"""
    month: str = Field(..., description="対象月（YYYY-MM形式）")
    days: List[DailyCensorshipStat] = Field(..., description="日別統計情報")

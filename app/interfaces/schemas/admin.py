from datetime import datetime
from typing import Optional

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

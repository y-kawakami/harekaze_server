import os
import uuid

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from app.domain.models.models import User
from app.domain.services.auth_service import AuthService
from app.infrastructure.database.database import get_db

router = APIRouter()

# __Host- プレフィックスは、Cookieのセキュリティを強化するためのプレフィックス。
# このプレフィックスを付けることで、以下の制約が課される:
# - Secure属性が必須 (HTTPS接続でのみ送信可能)
# - Domain属性の指定が禁止 (現在のホストのみに制限)
# - Path属性は "/" のみ許可
# 本番環境では __Host- プレフィックスを使用し、開発環境では省略する
# SESSION_TOKEN_KEY = "__Host-uiv19ekikv"
SESSION_TOKEN_KEY = "uiv19ekikv"

STAGE = os.getenv("stage", "dev")


@router.post("/auth/session")
async def create_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    セッション管理用のJWTトークンをCookieに設定する。
    こちら不要になりました。（互換のためにのこしておきます）
    """
    # クライアントのIPアドレスからユーザーを取得または作成
    auth_service = AuthService(db)
    client_ip = request.headers.get(
        "X-Forwarded-For") or getattr(request.client, "host", "unknown")
    user_uid = str(uuid.uuid4())
    user = auth_service.get_or_create_user(str(user_uid), client_ip)

    # JWTトークンを生成
    jwt_token = auth_service.create_session(user.uid)

    samesite = "none" if STAGE == "dev" else "lax"

    # Cookieを設定
    response.set_cookie(
        key=SESSION_TOKEN_KEY,
        value=jwt_token,
        httponly=True,  # JavaScriptからのアクセスを防ぐ
        secure=True,    # HTTPS接続でのみ送信
        samesite=samesite,
        max_age=60 * 60 * 24 * 30  # 30日間有効
    )

    return {"status": "success"}


async def get_current_user(
    request: Request,
    response: Response,
    session: str | None = Cookie(None, alias=SESSION_TOKEN_KEY),
    db: Session = Depends(get_db)
) -> User:
    """
    Cookieのセッショントークンからユーザーを取得する。
    セッションが存在しない、または無効な場合は新しいセッションを作成する。

    Args:
        request: リクエストオブジェクト
        response: レスポンスオブジェクト
        session: Cookieから取得したセッショントークン
        db: データベースセッション

    Returns:
        User: 認証されたユーザー
    """
    auth_service = AuthService(db)

    # 既存のセッションがある場合、検証を試みる
    if session:
        uid = auth_service.verify_token(session)
        if uid:
            user = db.query(User).filter(User.uid == uid).first()
            if user:
                return user

    # セッションがない、無効、またはユーザーが見つからない場合は新しいセッションを作成
    client_ip = request.headers.get(
        "X-Forwarded-For") or getattr(request.client, "host", "unknown")
    user_uid = str(uuid.uuid4())
    user = auth_service.get_or_create_user(str(user_uid), client_ip)

    # 新しいJWTトークンを生成してCookieに設定
    jwt_token = auth_service.create_session(user.uid)
    response.set_cookie(
        key=SESSION_TOKEN_KEY,
        value=jwt_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=60 * 60 * 24 * 30  # 30日間有効
    )

    return user

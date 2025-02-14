import uuid

from fastapi import (APIRouter, Cookie, Depends, HTTPException, Request,
                     Response)
from sqlalchemy.orm import Session

from app.domain.models.models import User
from app.domain.services.auth_service import AuthService
from app.infrastructure.database.database import get_db

router = APIRouter()


@router.post("/auth/session")
async def create_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    セッション管理用のJWTトークンをCookieに設定する。
    """
    # クライアントのIPアドレスからユーザーを取得または作成
    auth_service = AuthService(db)
    client_ip = request.headers.get(
        "X-Forwarded-For") or getattr(request.client, "host", "unknown")
    user_uid = str(uuid.uuid4())
    user = auth_service.get_or_create_user(str(user_uid), client_ip)

    # JWTトークンを生成
    jwt_token = auth_service.create_session(user.uid)

    # Cookieを設定
    response.set_cookie(
        key="session_token",
        value=jwt_token,
        httponly=True,  # JavaScriptからのアクセスを防ぐ
        secure=True,    # HTTPS接続でのみ送信
        # samesite="lax",  # CSRF対策
        samesite="none",  # クロスサイトリクエストを許可
        max_age=60 * 60 * 24 * 30  # 30日間有効
    )

    return {"status": "success"}


async def get_current_user(
    session: str | None = Cookie(None, alias="session_token"),
    db: Session = Depends(get_db)
) -> User:
    """
    Cookieのセッショントークンからユーザーを取得する。
    有効なセッションが存在しない場合は401エラーを返す。

    Args:
        session: Cookieから取得したセッショントークン
        db: データベースセッション

    Returns:
        User: 認証されたユーザー

    Raises:
        HTTPException: 認証に失敗した場合
    """
    if not session:
        raise HTTPException(
            status_code=401,
            detail="認証が必要です"
        )

    auth_service = AuthService(db)
    uid = auth_service.verify_token(session)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail="セッションが無効です"
        )

    user = db.query(User).filter(User.uid == uid).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="ユーザーが見つかりません"
        )

    return user

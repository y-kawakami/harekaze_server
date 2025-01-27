from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

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
    user = auth_service.get_or_create_user(client_ip)

    # JWTトークンを生成
    jwt_token = auth_service.create_session(str(user.id))

    # Cookieを設定
    response.set_cookie(
        key="session_token",
        value=jwt_token,
        httponly=True,  # JavaScriptからのアクセスを防ぐ
        secure=True,    # HTTPS接続でのみ送信
        samesite="lax",  # CSRF対策
        max_age=60 * 60 * 24 * 30  # 30日間有効
    )

    return {"status": "success"}

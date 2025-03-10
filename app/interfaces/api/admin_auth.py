from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.domain.models.models import Admin
from app.domain.services.auth_service import AuthService
from app.infrastructure.database.database import get_db
from app.interfaces.schemas.admin import AdminResponse, AdminToken

router = APIRouter(
    prefix="",
    tags=["admin"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin_api/login")


@router.post("/login", response_model=AdminToken)
async def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    管理者ログインAPI - JWTトークンを発行する
    """
    auth_service = AuthService(db)
    admin = auth_service.authenticate_admin(
        form_data.username, form_data.password)

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # JWTトークンを生成
    access_token = auth_service.create_admin_token(admin.id)

    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Admin:
    """
    現在の管理者を取得する依存関数

    Args:
        token: JWTトークン
        db: データベースセッション

    Returns:
        Admin: 認証された管理者

    Raises:
        HTTPException: 認証に失敗した場合
    """
    auth_service = AuthService(db)

    # トークンを検証
    admin_id = auth_service.verify_admin_token(token)
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証情報が無効です",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 管理者を取得
    admin = auth_service.get_admin_by_id(admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理者が見つかりません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return admin


@router.get("/me", response_model=AdminResponse)
async def read_admin_me(
    current_admin: Admin = Depends(get_current_admin)
):
    """
    現在ログインしている管理者の情報を取得する
    """
    return current_admin

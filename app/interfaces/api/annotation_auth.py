"""アノテーター認証APIエンドポイント

POST /annotation_api/login: ログイン・トークン発行
GET /annotation_api/me: 現在のアノテーター情報取得

Requirements: 1.1-1.5
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.domain.models.annotation import Annotator
from app.domain.services.annotation_auth_service import AnnotationAuthService
from app.infrastructure.database.database import get_db
from app.interfaces.schemas.annotation import AnnotatorResponse, AnnotatorToken

router = APIRouter(
    prefix="",
    tags=["annotation"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/annotation_api/login")


@router.post("/login", response_model=AnnotatorToken)
async def annotation_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> AnnotatorToken:
    """
    アノテーターログインAPI - JWTトークンを発行する
    """
    auth_service = AnnotationAuthService(db)
    annotator = auth_service.authenticate_annotator(
        form_data.username, form_data.password)

    if not annotator:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_annotator_token(annotator.id)

    return AnnotatorToken(access_token=access_token, token_type="bearer")


async def get_current_annotator(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Annotator:
    """
    現在のアノテーターを取得する依存関数

    Args:
        token: JWTトークン
        db: データベースセッション

    Returns:
        Annotator: 認証されたアノテーター

    Raises:
        HTTPException: 認証に失敗した場合
    """
    auth_service = AnnotationAuthService(db)

    annotator_id = auth_service.verify_annotator_token(token)
    if not annotator_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証情報が無効です",
            headers={"WWW-Authenticate": "Bearer"},
        )

    annotator = auth_service.get_annotator_by_id(annotator_id)
    if not annotator:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="アノテーターが見つかりません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return annotator


@router.get("/me", response_model=AnnotatorResponse)
async def read_annotator_me(
    current_annotator: Annotator = Depends(get_current_annotator)
) -> AnnotatorResponse:
    """
    現在ログインしているアノテーターの情報を取得する
    """
    return AnnotatorResponse(
        id=current_annotator.id,
        username=current_annotator.username,
        last_login=current_annotator.last_login,
        created_at=current_annotator.created_at,
    )

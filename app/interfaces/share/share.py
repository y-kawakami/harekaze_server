from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.application.share.share import create_share_response
from app.application.share.share_flowering import \
    create_share_flowering_response
from app.domain.services.image_service import ImageService, get_image_service
from app.infrastructure.database.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/interfaces/templates")


@router.get("/share", response_class=HTMLResponse)
async def share_html(
    request: Request,
    id: str = Query(
        ..., description="Tree ID"),
    type: int = Query(
        ..., description="Share Type(1 or 2)", ge=1, le=2),
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
):
    """
    シェア用のHTMLを表示する
    OGPメタ情報を含み、アプリにリダイレクトする
    """
    return create_share_response(
        request=request,
        tree_id=id,
        share_type=type,
        db=db,
        image_service=image_service,
        templates=templates,
    )


@router.get("/share/flowering", response_class=HTMLResponse)
async def share_flowering_html(
    request: Request,
    id: str = Query(
        ..., description="地点ID"),
    updated: str = Query(
        ..., description="更新日"),
):
    """
    シェア用のHTMLを表示する
    OGPメタ情報を含み、アプリにリダイレクトする
    """
    return create_share_flowering_response(
        request=request,
        id=id,
        updated=updated,
        templates=templates,
    )

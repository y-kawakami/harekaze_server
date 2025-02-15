from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.application.info.get_flowering_date import \
    get_flowering_date as get_flowering_date_app
from app.domain.models.models import User
from app.infrastructure.database.database import get_db
from app.interfaces.api.auth import get_current_user
from app.interfaces.schemas.tree import FloweringDateResponse

router = APIRouter()


@router.get("/info/flowering_date", response_model=FloweringDateResponse)
async def get_flowering_date(
    latitude: float = Query(
        ...,
        description="緯度"
    ),
    longitude: float = Query(
        ...,
        description="経度"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    桜の開花日に関する情報を取得する。
    """
    return get_flowering_date_app(
        db=db,
        current_user=current_user,
        latitude=latitude,
        longitude=longitude
    )

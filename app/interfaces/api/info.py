from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.infrastructure.database.database import get_db
from app.infrastructure.repositories.tree_repository import TreeRepository
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
    db: Session = Depends(get_db)
):
    """
    桜の開花日に関する情報を取得する。
    """
    repository = TreeRepository(db)
    flowering_info = repository.get_flowering_info(
        latitude=latitude,
        longitude=longitude
    )

    return {
        "address": flowering_info["address"],
        "flowering_date": flowering_info["flowering_date"],
        "full_bloom_date": flowering_info["full_bloom_date"]
    }

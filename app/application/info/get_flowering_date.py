from loguru import logger
from sqlalchemy.orm import Session

from app.domain.models.models import User
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import FloweringDateResponse


def get_flowering_date(
    db: Session,
    current_user: User,
    latitude: float,
    longitude: float,
) -> FloweringDateResponse:
    """
    桜の開花日に関する情報を取得する。

    Args:
        db (Session): データベースセッション
        current_user (User): 現在のユーザー
        latitude (float): 緯度
        longitude (float): 経度

    Returns:
        FloweringDateResponse: 開花日情報
    """
    logger.info(f"開花日情報の取得開始: 位置=({latitude}, {longitude})")

    repository = TreeRepository(db)
    flowering_info = repository.get_flowering_info(
        latitude=latitude,
        longitude=longitude
    )

    logger.info(f"開花日情報の取得完了: 住所={flowering_info['address']}")

    return FloweringDateResponse(
        address=flowering_info["address"],
        flowering_date=flowering_info["flowering_date"],
        full_bloom_date=flowering_info["full_bloom_date"]
    )

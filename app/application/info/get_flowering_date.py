from loguru import logger
from sqlalchemy.orm import Session

from app.application.exceptions import FloweringDateNotFoundError
from app.domain.models.models import User
from app.domain.services.flowering_date_service import FloweringDateService
from app.interfaces.schemas.tree import FloweringDateResponse


def get_flowering_date(
    db: Session,
    current_user: User,
    flowering_date_service: FloweringDateService,
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

    spot = flowering_date_service.find_nearest_spot(latitude, longitude)

    if spot:
        logger.info(f"開花日情報の取得完了: 住所={spot.address}")

        return FloweringDateResponse(
            spot_id=int(spot.spot_id),
            address=spot.address,
            flowering_date=spot.flowering_date.strftime("%Y-%m-%d"),
            full_bloom_date=spot.full_bloom_date.strftime("%Y-%m-%d"),
            full_bloom_end_date=spot.full_bloom_end_date.strftime("%Y-%m-%d"),
            variety=spot.variety,
            updated_date=spot.updated_date.strftime("%Y-%m-%d"),
        )
    else:
        raise FloweringDateNotFoundError(
            latitude=latitude, longitude=longitude)

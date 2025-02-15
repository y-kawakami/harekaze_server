from loguru import logger
from sqlalchemy.orm import Session

from app.application.exceptions import TreeNotFoundError
from app.domain.services.image_service import ImageService
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import (MushroomInfo, StemHoleInfo, StemInfo,
                                         TengusuInfo, TreeDetailResponse)


def get_tree_detail(
    db: Session,
    tree_id: str,
    image_service: ImageService,
) -> TreeDetailResponse:
    """
    各木の詳細情報を取得する。

    Args:
        db (Session): データベースセッション
        current_user (User): 現在のユーザー
        tree_id (str): 取得したい桜の木のUID
        image_service (ImageService): 画像サービス

    Returns:
        TreeDetailResponse: 木の詳細情報

    Raises:
        TreeNotFoundError: 指定された木が見つからない場合
    """
    logger.info(f"木の詳細情報取得開始: tree_id={tree_id}")

    repository = TreeRepository(db)
    tree = repository.get_tree(tree_id)
    if not tree:
        logger.warning(f"木が見つかりません: tree_id={tree_id}")
        raise TreeNotFoundError(tree_id=tree_id)

    response = TreeDetailResponse(
        id=tree.uid,
        tree_number=f"#{tree.id}",
        contributor=tree.contributor,
        latitude=tree.latitude,
        longitude=tree.longitude,
        location=tree.location,
        vitality=tree.vitality,
        prefecture_code=tree.prefecture_code or None,
        municipality_code=tree.municipality_code or None,
        image_url=image_service.get_image_url(str(tree.image_obj_key)),
        image_thumb_url=image_service.get_image_url(str(tree.thumb_obj_key)),
        decorated_image_url=image_service.get_image_url(
            tree.decorated_image_obj_key) if tree.decorated_image_obj_key else None,
        ogp_image_url=image_service.get_image_url(
            tree.ogp_image_obj_key) if tree.ogp_image_obj_key else None,
        stem=None,
        stem_hole=None,
        tengusu=None,
        mushroom=None,
        created_at=tree.created_at,
    )

    # 幹の情報を追加
    if tree.stem:
        response.stem = StemInfo(
            image_url=image_service.get_image_url(
                str(tree.stem.image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.stem.thumb_obj_key)),
            texture=tree.stem.texture,
            can_detected=tree.stem.can_detected,
            circumference=tree.stem.circumference,
            age=tree.stem.age,
            created_at=tree.stem.created_at,
        )

    # 幹の穴の情報を追加
    if tree.stem_holes:
        response.stem_hole = StemHoleInfo(
            image_url=image_service.get_image_url(
                str(tree.stem_holes[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.stem_holes[0].thumb_obj_key)),
            created_at=tree.stem_holes[0].created_at,
        )

    # テングス病の情報を追加
    if tree.tengus:
        response.tengusu = TengusuInfo(
            image_url=image_service.get_image_url(
                str(tree.tengus[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.tengus[0].thumb_obj_key)),
            created_at=tree.tengus[0].created_at,
        )

    # キノコの情報を追加
    if tree.mushrooms:
        response.mushroom = MushroomInfo(
            image_url=image_service.get_image_url(
                str(tree.mushrooms[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.mushrooms[0].thumb_obj_key)),
            created_at=tree.mushrooms[0].created_at,
        )

    logger.info(f"木の詳細情報取得完了: tree_id={tree_id}")
    return response

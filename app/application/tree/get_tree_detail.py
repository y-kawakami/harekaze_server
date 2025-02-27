from loguru import logger
from sqlalchemy.orm import Session

from app.application.exceptions import TreeNotFoundError
from app.domain.constants.anonymous import filter_anonymous
from app.domain.models.models import CensorshipStatus
from app.domain.services.image_service import ImageService
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import (KobuInfo, MushroomInfo, StemHoleInfo,
                                         StemInfo, TengusuInfo,
                                         TreeDetailResponse)


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

    # 木全体の検閲ステータスをチェック
    if tree.censorship_status != CensorshipStatus.APPROVED:
        logger.warning(
            f"木が検閲で承認されていません: tree_id={tree_id}, status={tree.censorship_status}")
        raise TreeNotFoundError(tree_id=tree_id)

    # EntireTreeの情報を準備
    vitality = None
    image_url = ""
    image_thumb_url = ""
    decorated_image_url = None
    ogp_image_url = None

    if tree.entire_tree and tree.entire_tree.censorship_status == CensorshipStatus.APPROVED:
        vitality = tree.entire_tree.vitality
        image_url = image_service.get_image_url(
            str(tree.entire_tree.image_obj_key))
        image_thumb_url = image_service.get_image_url(
            str(tree.entire_tree.thumb_obj_key))
        if tree.entire_tree.decorated_image_obj_key:
            decorated_image_url = image_service.get_image_url(
                tree.entire_tree.decorated_image_obj_key)
        if tree.entire_tree.ogp_image_obj_key:
            ogp_image_url = image_service.get_image_url(
                tree.entire_tree.ogp_image_obj_key)

    response = TreeDetailResponse(
        id=tree.uid,
        tree_number=f"#{tree.id}",
        contributor=filter_anonymous(
            tree.contributor) if tree.contributor else tree.contributor,
        latitude=tree.latitude,
        longitude=tree.longitude,
        location=tree.location,
        vitality=vitality,
        prefecture_code=tree.prefecture_code or None,
        municipality_code=tree.municipality_code or None,
        image_url=image_url,
        image_thumb_url=image_thumb_url,
        decorated_image_url=decorated_image_url,
        ogp_image_url=ogp_image_url,
        stem=None,
        stem_hole=None,
        tengusu=None,
        mushroom=None,
        kobu=None,
        created_at=tree.created_at,
    )

    # 幹の情報を追加（検閲ステータスを確認）
    if tree.stem and tree.stem.censorship_status == CensorshipStatus.APPROVED:
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

    # 幹の穴の情報を追加（検閲ステータスを確認）
    if tree.stem_holes and tree.stem_holes[0].censorship_status == CensorshipStatus.APPROVED:
        response.stem_hole = StemHoleInfo(
            image_url=image_service.get_image_url(
                str(tree.stem_holes[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.stem_holes[0].thumb_obj_key)),
            created_at=tree.stem_holes[0].created_at,
        )

    # テングス病の情報を追加（検閲ステータスを確認）
    if tree.tengus and tree.tengus[0].censorship_status == CensorshipStatus.APPROVED:
        response.tengusu = TengusuInfo(
            image_url=image_service.get_image_url(
                str(tree.tengus[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.tengus[0].thumb_obj_key)),
            created_at=tree.tengus[0].created_at,
        )

    # キノコの情報を追加（検閲ステータスを確認）
    if tree.mushrooms and tree.mushrooms[0].censorship_status == CensorshipStatus.APPROVED:
        response.mushroom = MushroomInfo(
            image_url=image_service.get_image_url(
                str(tree.mushrooms[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.mushrooms[0].thumb_obj_key)),
            created_at=tree.mushrooms[0].created_at,
        )

    # こぶ状の枝の情報を追加（検閲ステータスを確認）
    if tree.kobus and tree.kobus[0].censorship_status == CensorshipStatus.APPROVED:
        response.kobu = KobuInfo(
            image_url=image_service.get_image_url(
                str(tree.kobus[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.kobus[0].thumb_obj_key)),
            created_at=tree.kobus[0].created_at,
        )

    logger.info(f"木の詳細情報取得完了: tree_id={tree_id}")
    return response

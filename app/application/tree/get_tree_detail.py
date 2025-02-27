from typing import Optional

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
    current_user_id: Optional[int] = None,
) -> TreeDetailResponse:
    """
    各木の詳細情報を取得する。

    Args:
        db (Session): データベースセッション
        tree_id (str): 取得したい桜の木のUID
        image_service (ImageService): 画像サービス
        current_user_id (Optional[int]): 現在のユーザーID（ユーザー自身の投稿を確認する場合に使用）

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

    # 自分の投稿かどうかをチェック
    is_own_post = current_user_id is not None and tree.user_id == current_user_id

    # 木全体の検閲ステータスをチェック（自分の投稿の場合はスキップ）
    if not is_own_post and tree.censorship_status != CensorshipStatus.APPROVED:
        logger.warning(
            f"木が検閲で承認されていません: tree_id={tree_id}, status={tree.censorship_status}")
        raise TreeNotFoundError(tree_id=tree_id)

    # EntireTreeの情報を準備
    vitality = None
    image_url = ""
    image_thumb_url = ""
    decorated_image_url = None
    ogp_image_url = None

    # 自分の投稿か検閲ステータスがAPPROVEDの場合に情報を表示
    if tree.entire_tree and (is_own_post or tree.entire_tree.censorship_status == CensorshipStatus.APPROVED):
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
        # 自分の投稿の場合は検閲ステータスも追加
        censorship_status=tree.censorship_status if is_own_post else None
    )

    # 幹の情報を追加（自分の投稿か検閲ステータスがAPPROVEDの場合）
    if tree.stem and (is_own_post or tree.stem.censorship_status == CensorshipStatus.APPROVED):
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
            censorship_status=tree.stem.censorship_status if is_own_post else None
        )

    # 幹の穴の情報を追加（自分の投稿か検閲ステータスがAPPROVEDの場合）
    if tree.stem_holes and (is_own_post or tree.stem_holes[0].censorship_status == CensorshipStatus.APPROVED):
        response.stem_hole = StemHoleInfo(
            image_url=image_service.get_image_url(
                str(tree.stem_holes[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.stem_holes[0].thumb_obj_key)),
            created_at=tree.stem_holes[0].created_at,
            censorship_status=tree.stem_holes[0].censorship_status if is_own_post else None
        )

    # テングス病の情報を追加（自分の投稿か検閲ステータスがAPPROVEDの場合）
    if tree.tengus and (is_own_post or tree.tengus[0].censorship_status == CensorshipStatus.APPROVED):
        response.tengusu = TengusuInfo(
            image_url=image_service.get_image_url(
                str(tree.tengus[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.tengus[0].thumb_obj_key)),
            created_at=tree.tengus[0].created_at,
            censorship_status=tree.tengus[0].censorship_status if is_own_post else None
        )

    # キノコの情報を追加（自分の投稿か検閲ステータスがAPPROVEDの場合）
    if tree.mushrooms and (is_own_post or tree.mushrooms[0].censorship_status == CensorshipStatus.APPROVED):
        response.mushroom = MushroomInfo(
            image_url=image_service.get_image_url(
                str(tree.mushrooms[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.mushrooms[0].thumb_obj_key)),
            created_at=tree.mushrooms[0].created_at,
            censorship_status=tree.mushrooms[0].censorship_status if is_own_post else None
        )

    # こぶ状の枝の情報を追加（自分の投稿か検閲ステータスがAPPROVEDの場合）
    if tree.kobus and (is_own_post or tree.kobus[0].censorship_status == CensorshipStatus.APPROVED):
        response.kobu = KobuInfo(
            image_url=image_service.get_image_url(
                str(tree.kobus[0].image_obj_key)),
            image_thumb_url=image_service.get_image_url(
                str(tree.kobus[0].thumb_obj_key)),
            created_at=tree.kobus[0].created_at,
            censorship_status=tree.kobus[0].censorship_status if is_own_post else None
        )

    # 自分の投稿の場合はログにその旨を記録
    if is_own_post:
        logger.info(
            f"投稿者自身による木の詳細情報取得: tree_id={tree_id}, user_id={current_user_id}")

    logger.info(f"木の詳細情報取得完了: tree_id={tree_id}")
    return response

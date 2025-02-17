import uuid

from loguru import logger
from sqlalchemy.orm import Session

from app.application.exceptions import (DatabaseError, ImageUploadError,
                                        TreeNotFoundError)
from app.domain.models.models import User
from app.domain.services.image_service import ImageService
from app.infrastructure.repositories.stem_repository import StemRepository
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import StemInfo


def create_stem(
    db: Session,
    current_user: User,
    tree_id: str,
    image_data: bytes,
    latitude: float,
    longitude: float,
    image_service: ImageService,
) -> StemInfo:
    """
    幹の写真を登録する。既存の幹の写真がある場合は削除して新規登録する。

    Args:
        db (Session): データベースセッション
        current_user (User): 現在のユーザー
        tree_id (str): 幹の写真を登録する木のUID
        image_data (bytes): 幹の写真データ
        latitude (float): 撮影場所の緯度
        longitude (float): 撮影場所の経度
        image_service (ImageService): 画像サービス

    Returns:
        StemInfo: 登録された幹の情報

    Raises:
        TreeNotFoundError: 指定された木が見つからない場合
        ImageUploadError: 画像のアップロードに失敗した場合
    """
    logger.info(f"幹の写真登録開始: tree_id={tree_id}")

    # 木の取得
    tree_repository = TreeRepository(db)
    tree = tree_repository.get_tree(tree_id)
    if not tree:
        logger.warning(f"木が見つかりません: tree_id={tree_id}")
        raise TreeNotFoundError(tree_id=tree_id)

    # 既存の幹の写真があれば削除
    stem_repository = StemRepository(db)
    existing_stem = stem_repository.get_stem_by_tree_id(tree.id)
    if existing_stem:
        logger.info(f"既存の幹の写真を削除: tree_id={tree_id}")
        try:
            # S3から画像を削除
            if existing_stem.image_obj_key:
                image_service.delete_image(existing_stem.image_obj_key)
            if existing_stem.thumb_obj_key:
                image_service.delete_image(existing_stem.thumb_obj_key)

            # DBから削除
            stem_repository.delete_stem(existing_stem.id)
        except Exception as e:
            logger.error(f"既存の幹の写真の削除中にエラー発生: {str(e)}")
            # 削除に失敗しても続行

    # 画像を解析
    logger.debug("幹の画像解析を開始")
    texture, can_detected, circumference, age = image_service.analyze_stem_image(
        image_data)

    # サムネイル作成
    logger.debug("サムネイル作成を開始")
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"trees/{tree.id}/stem_{random_suffix}.jpg"
    thumb_key = f"trees/{tree.id}/stem_thumb_{random_suffix}.jpg"

    try:
        if not (image_service.upload_image(image_data, image_key) and
                image_service.upload_image(thumb_data, thumb_key)):
            logger.error(f"画像アップロード失敗: tree_id={tree_id}")
            raise ImageUploadError(tree_uid=tree_id)
        logger.debug(f"画像アップロード成功: image_key={image_key}")
    except Exception as e:
        logger.exception(f"画像アップロード中にエラー発生: {str(e)}")
        raise ImageUploadError(tree_uid=tree_id) from e

    # DBに保存
    try:
        stem_repository.create_stem(
            tree_id=tree.id,
            user_id=current_user.id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_key,
            thumb_obj_key=thumb_key,
            texture=texture,
            can_detected=can_detected,
            circumference=circumference,
            age=age,
        )
        logger.info(f"幹の写真登録完了: tree_id={tree_id}")
    except Exception as e:
        logger.exception(f"DB登録中にエラー発生: {str(e)}")
        raise DatabaseError(message=str(e)) from e

    return StemInfo(
        texture=texture,
        can_detected=can_detected,
        circumference=circumference,
        age=age,
        image_url=image_service.get_image_url(image_key),
        image_thumb_url=image_service.get_image_url(thumb_key),
        created_at=tree.created_at
    )

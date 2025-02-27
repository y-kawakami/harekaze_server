import uuid
from datetime import datetime
from typing import Optional

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
    photo_date: Optional[str] = None
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
        photo_date (Optional[str]): 撮影日時（ISO8601形式）

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

    if tree.user_id != current_user.id:
        logger.warning(f"木の所有者ではないユーザーが幹の写真を登録しようとしました: tree_id={tree_id}")
        raise DatabaseError(message="他のユーザーの木に対して幹の写真を登録することはできません")

    # 画像の解析
    texture, can_detected, circumference, age = image_service.analyze_stem_image(
        image_data)

    # サムネイル作成
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"{tree_id}/stem_{random_suffix}.jpg"
    thumb_key = f"{tree_id}/stem_thumb_{random_suffix}.jpg"

    try:
        image_service.upload_image(image_data, image_key)
        image_service.upload_image(thumb_data, thumb_key)
    except Exception as e:
        logger.exception(f"画像アップロード中にエラー発生: {str(e)}")
        raise ImageUploadError(tree_id) from e

    # 日時の解析
    parsed_photo_date = None
    if photo_date:
        try:
            parsed_photo_date = datetime.fromisoformat(
                photo_date.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(
                f"Invalid date format: {photo_date}, using current time instead")

    # 幹の情報を保存
    stem_repository = StemRepository(db)
    try:
        # 既存の記録があれば削除
        stem_repository.delete_stem_for_tree(tree.id)

        # 新規作成
        stem = stem_repository.create_stem(
            user_id=current_user.id,
            tree_id=tree.id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_key,
            thumb_obj_key=thumb_key,
            can_detected=can_detected,
            circumference=circumference if can_detected else None,
            texture=texture,
            age=age,
            photo_date=parsed_photo_date
        )
        logger.info(f"幹の写真登録完了: stem_id={stem.id}")

        # レスポンス用情報取得
        image_url = image_service.get_image_url(stem.image_obj_key)
        thumb_url = image_service.get_image_url(stem.thumb_obj_key)

        return StemInfo(
            image_url=image_url,
            image_thumb_url=thumb_url,
            texture=stem.texture,
            can_detected=stem.can_detected,
            circumference=stem.circumference,
            age=stem.age,
            censorship_status=stem.censorship_status,
            created_at=stem.photo_date
        )
    except Exception as e:
        logger.exception(f"幹の情報保存中にエラー発生: {str(e)}")
        raise DatabaseError(message="幹の情報の保存に失敗しました") from e

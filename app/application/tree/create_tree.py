import uuid

from loguru import logger
from sqlalchemy.orm import Session

from app.application.exceptions import (DatabaseError, ImageUploadError,
                                        TreeNotDetectedError)
from app.domain.models.models import User
from app.domain.services.image_service import ImageService
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import TreeResponse

image_service = ImageService()


def create_tree(
    db: Session,
    current_user: User,
    latitude: float,
    longitude: float,
    image_data: bytes,
    nickname: str,
) -> TreeResponse:
    """
    桜の木全体の写真を登録する。

    Args:
        db (Session): データベースセッション
        current_user (User): 現在のユーザー
        latitude (float): 撮影場所の緯度
        longitude (float): 撮影場所の経度
        image_data (bytes): 画像データ
        nickname (str): 投稿者のニックネーム

    Returns:
        TreeResponse: 作成された木の情報

    Raises:
        TreeNotDetectedError: 木が検出できない場合
        ImageUploadError: 画像のアップロードに失敗した場合
        DatabaseError: データベースの操作に失敗した場合
    """
    logger.info(
        f"新しい木の登録を開始: ユーザーID={current_user.id}, 位置={latitude},{longitude}")

    # 画像を解析
    logger.debug("画像解析を開始")
    vitality, tree_detected = image_service.analyze_tree_vitality(image_data)
    if not tree_detected:
        logger.warning(f"木が検出できません: ユーザーID={current_user.id}")
        raise TreeNotDetectedError(user_id=current_user.id)

    # サムネイル作成
    logger.debug("サムネイル作成を開始")
    thumb_data = image_service.create_thumbnail(image_data)

    # UIDを生成
    tree_uid = str(uuid.uuid4())
    logger.debug(f"生成されたツリーUID: {tree_uid}")

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"{tree_uid}/entire_{random_suffix}.jpg"
    thumb_key = f"{tree_uid}/entire_thumb_{random_suffix}.jpg"

    try:
        if not (image_service.upload_image(image_data, image_key) and
                image_service.upload_image(thumb_data, thumb_key)):
            logger.error(f"画像アップロード失敗: ツリーUID={tree_uid}")
            raise ImageUploadError(tree_uid=tree_uid)
        logger.debug(f"画像アップロード成功: image_key={image_key}")
    except Exception as e:
        logger.exception(f"画像アップロード中にエラー発生: {str(e)}")
        raise ImageUploadError(tree_uid=tree_uid) from e

    # DBに登録
    try:
        repository = TreeRepository(db)
        tree = repository.create_tree(
            user_id=current_user.id,
            uid=tree_uid,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_key,
            thumb_obj_key=thumb_key,
            vitality=vitality,
            position=f'POINT({longitude} {latitude})',
            location="東京都多摩市",  # TODO: 逆ジオコーディングAPIから取得
            prefecture_code="13",  # TODO: 逆ジオコーディングAPIから取得
            municipality_code="132241"  # TODO: 逆ジオコーディングAPIから取得
        )
        logger.info(f"木の登録が完了: ツリーUID={tree_uid}, 元気度={vitality}")
    except Exception as e:
        logger.exception(f"DB登録中にエラー発生: {str(e)}")
        raise DatabaseError(message=str(e)) from e

    return TreeResponse(
        id=tree.uid,
        tree_number=f"#{tree.id}",
        latitude=tree.latitude,
        longitude=tree.longitude,
        location=tree.location,
        prefecture_code=tree.prefecture_code,
        municipality_code=tree.municipality_code,
        vitality=tree.vitality,
        created_at=tree.created_at
    )

import uuid
from typing import Optional

from loguru import logger
from PIL import ImageOps
from sqlalchemy.orm import Session

from app.application.exceptions import (DatabaseError, ImageUploadError,
                                        InvalidParamError, TreeNotFoundError)
from app.domain.models.models import CensorshipStatus, User
from app.domain.services.image_service import ImageService
from app.domain.utils import blur
from app.domain.utils.date_utils import DateUtils
from app.infrastructure.images.label_detector import LabelDetector
from app.infrastructure.repositories.mushroom_repository import \
    MushroomRepository
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import MushroomInfo


async def create_mushroom(
    db: Session,
    current_user: User,
    tree_id: str,
    image_data: bytes,
    latitude: float,
    longitude: float,
    image_service: ImageService,
    label_detector: LabelDetector,
    photo_date: Optional[str] = None,
    is_approved_debug: bool = False
) -> MushroomInfo:
    """
    キノコの写真を登録する。既存のキノコの写真がある場合は削除して新規登録する。

    Args:
        db (Session): データベースセッション
        current_user (User): 現在のユーザー
        tree_id (str): キノコの写真を登録する木のUID
        image_data (bytes): キノコの写真データ
        latitude (float): 撮影場所の緯度
        longitude (float): 撮影場所の経度
        image_service (ImageService): 画像サービス
        photo_date (Optional[str]): 撮影日時（ISO8601形式）
        is_approved_debug (bool): デバッグ用に承認済みとしてマークするフラグ

    Returns:
        MushroomInfo: 登録されたキノコの情報

    Raises:
        TreeNotFoundError: 指定された木が見つからない場合
        ImageUploadError: 画像のアップロードに失敗した場合
        DatabaseError: データベースの操作に失敗した場合
        InvalidParamError: 不正なパラメータが指定された場合
    """
    logger.info(f"キノコの写真登録開始: tree_id={tree_id}")

    # 木の取得
    tree_repository = TreeRepository(db)
    tree = tree_repository.get_tree(tree_id)
    if not tree:
        logger.warning(f"木が見つかりません: tree_id={tree_id}")
        raise TreeNotFoundError(tree_id=tree_id)

    '''
    if tree.user_id != current_user.id:
        logger.warning(f"木の所有者ではないユーザーが幹の写真を登録しようとしました: tree_id={tree_id}")
        raise ForbiddenError("この木に対して写真を登録することはできません")
    '''

    # 日時の解析
    parsed_photo_date = None
    if photo_date:
        parsed_photo_date = DateUtils.parse_iso_date(photo_date)
        if not parsed_photo_date:
            logger.warning(f"不正な日時形式: {photo_date}")
            raise InvalidParamError(
                reason=f"不正な日時形式です: {photo_date}",
                param_name="photo_date"
            )

    image = image_service.bytes_to_pil(image_data)
    rotated_image = ImageOps.exif_transpose(
        image, in_place=True)  # EXIF情報に基づいて適切に回転
    if rotated_image is not None:
        image = rotated_image

    labels = label_detector.detect(image, ['Person'])

    # 人物をぼかす
    logger.debug("ぼかしを開始")
    person_labels = labels.get('Person', [])
    if len(person_labels) > 0:
        logger.debug("人物が検出されたためぼかしを適用")
        blurred_image = blur.apply_blur_to_bbox(
            image, person_labels)
        image_data = image_service.pil_to_bytes(blurred_image, 'jpeg')
        image = blurred_image

    # 既存のキノコの写真があれば削除
    mushroom_repository = MushroomRepository(db)
    existing_mushrooms = mushroom_repository.get_mushrooms_by_tree_id(tree.id)
    if existing_mushrooms:
        logger.info(f"既存のキノコの写真を削除: tree_id={tree_id}")
        for mushroom in existing_mushrooms:
            try:
                # S3から画像を削除
                if mushroom.image_obj_key:
                    await image_service.delete_image(mushroom.image_obj_key)
                if mushroom.thumb_obj_key:
                    await image_service.delete_image(mushroom.thumb_obj_key)

                # DBから削除
                mushroom_repository.delete_mushroom(mushroom.id)
            except Exception as e:
                logger.error(f"既存のキノコの写真の削除中にエラー発生: {str(e)}")
                # 削除に失敗しても続行

    # サムネイル作成
    logger.debug("サムネイル作成を開始")
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"{tree.uid}/mushroom_{random_suffix}.jpg"
    thumb_key = f"{tree.uid}/mushroom_thumb_{random_suffix}.jpg"

    try:
        if not (await image_service.upload_image(image_data, image_key) and
                await image_service.upload_image(thumb_data, thumb_key)):
            logger.error(f"画像アップロード失敗: tree_id={tree_id}")
            raise ImageUploadError(tree_uid=tree_id)
        logger.debug(f"画像アップロード成功: image_key={image_key}")
    except Exception as e:
        logger.exception(f"画像アップロード中にエラー発生: {str(e)}")
        raise ImageUploadError(tree_uid=tree_id) from e

    # DBに保存
    try:
        mushroom = mushroom_repository.create_mushroom(
            tree_id=tree.id,
            user_id=current_user.id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_key,
            thumb_obj_key=thumb_key,
            photo_date=parsed_photo_date
        )

        # デバッグモードでの自動承認
        if is_approved_debug:
            logger.info(f"デバッグモードによる自動承認: キノコID={mushroom.id}")
            mushroom.censorship_status = CensorshipStatus.APPROVED
            db.commit()

        logger.info(f"キノコの写真登録完了: tree_id={tree_id}")

        # 画像URLの取得
        image_url = image_service.get_image_url(image_key)
        thumb_url = image_service.get_image_url(thumb_key)

        return MushroomInfo(
            image_url=image_url,
            image_thumb_url=thumb_url,
            created_at=mushroom.photo_date,
            censorship_status=mushroom.censorship_status,
        )
    except Exception as e:
        logger.exception(f"DB登録中にエラー発生: {str(e)}")
        raise DatabaseError(message=str(e)) from e

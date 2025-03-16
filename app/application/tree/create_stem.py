import asyncio
import time as time_module  # 時間計測用にtimeモジュールをインポート
import uuid
from datetime import datetime
from typing import Optional

from loguru import logger
from PIL import ImageOps
from sqlalchemy.orm import Session

from app.application.common.constants import CAN_WIDTH_MM
from app.application.exceptions import (CanNotDetectedError, DatabaseError,
                                        ImageUploadError, TreeNotDetectedError,
                                        TreeNotFoundError)
from app.domain.models.bounding_box import BoundingBox
from app.domain.models.models import CensorshipStatus, User
from app.domain.models.tree_age import (estimate_tree_age,
                                        estimate_tree_age_from_texture,
                                        estimate_tree_age_with_prefecture)
from app.domain.services.ai_service import AIService
from app.domain.services.image_service import ImageService
from app.domain.utils import blur
from app.infrastructure.images.label_detector import LabelDetector
from app.infrastructure.repositories.stem_repository import StemRepository
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import StemInfo


async def create_stem(
    db: Session,
    current_user: User,
    tree_id: str,
    image_data: bytes,
    latitude: float,
    longitude: float,
    image_service: ImageService,
    label_detector: LabelDetector,
    ai_service: AIService,
    photo_date: Optional[str] = None,
    is_can_rquired: bool = False,
    is_approved_debug: bool = False,
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
        label_detector (LabelDetector): ラベル検出器
        ai_service (AIService): AI呼び出しサービス
        photo_date (Optional[str]): 撮影日時（ISO8601形式）
        is_can_rquired (bool): 缶の検出が必須かどうか
        is_approved_debug (bool): デバッグ用に承認済みとしてマークするフラグ

    Returns:
        StemInfo: 登録された幹の情報

    Raises:
        TreeNotFoundError: 指定された木が見つからない場合
        ImageUploadError: 画像のアップロードに失敗した場合
    """
    start_time_total = time_module.time()
    logger.info(f"幹の写真登録開始: tree_id={tree_id}")

    # 木の取得
    start_time = time_module.time()
    tree_repository = TreeRepository(db)
    tree = tree_repository.get_tree(tree_id)
    if not tree:
        logger.warning(f"木が見つかりません: tree_id={tree_id}")
        raise TreeNotFoundError(tree_id=tree_id)
    end_time = time_module.time()
    logger.info(f"木の取得処理: {(end_time - start_time) * 1000:.2f}ms")

    '''
    if tree.user_id != current_user.id:
        logger.warning(f"木の所有者ではないユーザーが幹の写真を登録しようとしました: tree_id={tree_id}")
        raise ForbiddenError("この木に対して写真を登録することはできません")
    '''

    # 画像の前処理
    start_time = time_module.time()
    image = image_service.bytes_to_pil(image_data)
    rotated_image = ImageOps.exif_transpose(
        image, in_place=True)  # EXIF情報に基づいて適切に回転
    if rotated_image is not None:
        image = rotated_image
        image_data = image_service.pil_to_bytes(image, 'jpeg')
    end_time = time_module.time()
    logger.info(f"画像の前処理: {(end_time - start_time) * 1000:.2f}ms")

    # ラベル検出
    start_time = time_module.time()
    labels = await label_detector.detect(image, ['Tree', 'Person', 'Can'])
    if "Tree" not in labels:
        logger.warning(f"木が検出できません: ユーザーID={current_user.id}")
        raise TreeNotDetectedError()

    can_bboxes = labels.get("Can", [])
    # 一番confidenceの高い缶を取得
    most_confident_can: Optional[BoundingBox] = None
    max_confidence = 0.0
    for bbox in can_bboxes:
        if bbox.confidence > max_confidence:
            max_confidence = bbox.confidence
            most_confident_can = bbox
    if is_can_rquired and most_confident_can is None:
        raise CanNotDetectedError("缶が検出できません")
    end_time = time_module.time()
    logger.info(f"ラベル検出処理: {(end_time - start_time) * 1000:.2f}ms")

    # Lambda入力画像をアップロード
    start_time = time_module.time()
    orig_suffix = str(uuid.uuid4())
    orig_image_key = f"{tree_id}/stem_orig_{orig_suffix}.jpg"
    debug_key = f"{tree_id}/stem_debug_{orig_suffix}.jpg"
    bucket_name = image_service.get_contents_bucket_name()

    # 画像のアップロードと解析を同時に実行
    logger.debug("画像のアップロードと解析を同時に開始")

    # 2つのタスクを同時に実行
    upload_task = image_service.upload_image(image_data, orig_image_key)
    analyze_task = ai_service.analyze_stem(
        image_bytes=image_data,
        filename='image.jpg',
        can_bbox=most_confident_can,
        can_width_mm=CAN_WIDTH_MM,
        output_bucket=bucket_name,
        output_key=image_service.get_full_object_key(debug_key)
    )

    # 両方のタスクが完了するまで待機
    upload_result, result = await asyncio.gather(upload_task, analyze_task)
    if upload_result is False:
        logger.error("画像のアップロードに失敗しました")
        raise ImageUploadError('internal')

    end_time = time_module.time()
    logger.info(f"画像のアップロードと解析処理: {(end_time - start_time) * 1000:.2f}ms")

    # 人物をぼかす
    start_time = time_module.time()
    logger.debug("ぼかしを開始")
    person_labels = labels.get('Person', [])
    if len(person_labels) > 0:
        logger.debug("人物が検出されたためぼかしを適用")
        blurred_image = blur.apply_blur_to_bbox(
            image, person_labels)
        image_data = image_service.pil_to_bytes(blurred_image, 'jpeg')
        image = blurred_image
    end_time = time_module.time()
    logger.info(f"人物ぼかし処理: {(end_time - start_time) * 1000:.2f}ms")

    # サムネイル作成
    start_time = time_module.time()
    logger.debug("サムネイル作成を開始")
    thumb_data = image_service.create_thumbnail(image_data)
    end_time = time_module.time()
    logger.info(f"サムネイル作成: {(end_time - start_time) * 1000:.2f}ms")

    # 画像をアップロード
    start_time = time_module.time()
    random_suffix = str(uuid.uuid4())
    image_key = f"{tree_id}/stem_{random_suffix}.jpg"
    thumb_key = f"{tree_id}/stem_thumb_{random_suffix}.jpg"
    try:
        await image_service.upload_image(image_data, image_key)
        await image_service.upload_image(thumb_data, thumb_key)
    except Exception as e:
        logger.exception(f"画像アップロード中にエラー発生: {str(e)}")
        raise ImageUploadError(tree_id) from e
    end_time = time_module.time()
    logger.info(f"画像とサムネイルのアップロード: {(end_time - start_time) * 1000:.2f}ms")

    # 日時の解析
    start_time = time_module.time()
    parsed_photo_date = None
    if photo_date:
        try:
            parsed_photo_date = datetime.fromisoformat(
                photo_date.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(
                f"Invalid date format: {photo_date}, using current time instead")
    end_time = time_module.time()
    logger.info(f"日時解析処理: {(end_time - start_time) * 1000:.2f}ms")

    # 幹の情報を保存
    start_time = time_module.time()
    stem_repository = StemRepository(db)
    try:
        # 既存の記録があれば削除
        stem_repository.delete_stem_for_tree(tree.id)

        age = 0
        age_texture = estimate_tree_age_from_texture(result.smoothness_real)
        age_circumference: Optional[int] = None
        diameter = result.diameter_mm * 0.1 if result.diameter_mm else None
        if diameter:
            age_c = 0
            if tree.prefecture_code:
                age_c = estimate_tree_age_with_prefecture(
                    diameter, tree.prefecture_code)
            else:
                age_c = round(estimate_tree_age(diameter))
            age_circumference = round(age_c)
            age = round((age_texture + age_c) / 2.0)
        else:
            age = round(age_texture)

        # 新規作成
        stem = stem_repository.create_stem(
            user_id=current_user.id,
            tree_id=tree.id,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_key,
            thumb_obj_key=thumb_key,
            can_detected=most_confident_can is not None,
            can_width_mm=CAN_WIDTH_MM if most_confident_can else None,
            circumference=result.diameter_mm * 0.1 if result.diameter_mm else None,
            texture=result.smoothness,
            texture_real=result.smoothness_real,
            age=age,
            age_texture=round(age_texture),
            age_circumference=age_circumference,
            photo_date=parsed_photo_date,
            debug_image_obj_key=debug_key
        )

        # デバッグモードでの自動承認
        if is_approved_debug:
            logger.info(f"デバッグモードによる自動承認: 幹ID={stem.id}")
            stem.censorship_status = CensorshipStatus.APPROVED
            db.commit()

        logger.info(f"幹の写真登録完了: stem_id={stem.id}")
        end_time = time_module.time()
        logger.info(f"幹情報の保存処理: {(end_time - start_time) * 1000:.2f}ms")

        # レスポンス用情報取得
        start_time = time_module.time()
        image_url = image_service.get_image_url(stem.image_obj_key)
        thumb_url = image_service.get_image_url(stem.thumb_obj_key)
        end_time = time_module.time()
        logger.info(f"URL取得処理: {(end_time - start_time) * 1000:.2f}ms")

        end_time_total = time_module.time()
        logger.info(
            f"幹の写真登録処理全体: {(end_time_total - start_time_total) * 1000:.2f}ms")

        return StemInfo(
            image_url=image_url,
            image_thumb_url=thumb_url,
            texture=stem.texture,
            texture_real=stem.texture_real,
            can_detected=stem.can_detected,
            circumference=stem.circumference,
            age=stem.age,
            age_texture=stem.age_texture,
            age_circumference=stem.age_circumference,
            censorship_status=stem.censorship_status,
            created_at=stem.photo_date,
            analysis_image_url=None
        )
    except Exception as e:
        logger.exception(f"幹の情報保存中にエラー発生: {str(e)}")
        raise DatabaseError(message="幹の情報の保存に失敗しました") from e

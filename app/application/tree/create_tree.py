import asyncio
import datetime
import uuid
from typing import Optional

from loguru import logger
from PIL import ImageOps
from sqlalchemy.orm import Session

from app.application.exceptions import (DatabaseError, ImageUploadError,
                                        InvalidParamError,
                                        LocationNotFoundError,
                                        LocationNotInJapanError, NgWordError,
                                        TreeNotDetectedError)
from app.domain.constants.anonymous import filter_anonymous
from app.domain.constants.ngwords import is_ng_word
from app.domain.models.models import CensorshipStatus, User
from app.domain.services.flowering_date_service import FloweringDateService
from app.domain.services.image_service import ImageService
from app.domain.services.lambda_service import LambdaService
from app.domain.utils import blur
from app.domain.utils.date_utils import DateUtils
from app.infrastructure.geocoding.geocoding_service import GeocodingService
from app.infrastructure.images.label_detector import LabelDetector
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import TreeResponse


async def create_tree(
    db: Session,
    current_user: User,
    latitude: float,
    longitude: float,
    image_data: bytes,
    contributor: Optional[str],
    image_service: ImageService,
    geocoding_service: GeocodingService,
    label_detector: LabelDetector,
    flowering_date_service: FloweringDateService,
    lambda_service: LambdaService,
    photo_date: Optional[str] = None,
    is_approved_debug: bool = False,
    detail_debug: bool = False
) -> TreeResponse:
    """
    桜の木全体の写真を登録する。

    Args:
        db (Session): データベースセッション
        current_user (User): 現在のユーザー
        latitude (float): 撮影場所の緯度
        longitude (float): 撮影場所の経度
        image_data (bytes): 画像データ
        contributor (str): 投稿者のニックネーム
        image_service (ImageService): 画像サービス
        geocoding_service (GeocodingService): 位置情報サービス
        photo_date (Optional[str]): 撮影日時（ISO8601形式）
        is_approved_debug (bool): デバッグ用に承認済みとしてマークするフラグ

    Returns:
        TreeResponse: 作成された木の情報

    Raises:
        TreeNotDetectedError: 木が検出できない場合
        ImageUploadError: 画像のアップロードに失敗した場合
        DatabaseError: データベースの操作に失敗した場合
    """

    if contributor is not None and is_ng_word(contributor):
        raise NgWordError(contributor)

    logger.info(
        f"新しい木の登録を開始: ユーザーID={current_user.id}, 位置={latitude},{longitude}")

    address = geocoding_service.get_address(latitude, longitude)
    if address.country is None:
        logger.warning(f"指定された場所が見つかりません: ({latitude}, {longitude})")
        raise LocationNotFoundError(latitude=latitude, longitude=longitude)
    if address.country != "日本":
        logger.warning(f"日本国内の場所を指定してください: ({latitude}, {longitude})")
        raise LocationNotInJapanError(latitude=latitude, longitude=longitude)
    if address.detail is None or address.prefecture_code is None or address.municipality_code is None:
        logger.warning(f"住所情報が不足しています: ({latitude}, {longitude})")
        raise LocationNotFoundError(latitude=latitude, longitude=longitude)

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

    labels = label_detector.detect(image, ['Tree', 'Person'])
    print(labels)
    if "Tree" not in labels:
        logger.warning(f"木が検出できません: ユーザーID={current_user.id}")
        raise TreeNotDetectedError()

    # UIDを生成
    tree_id = str(uuid.uuid4())
    logger.debug(f"生成されたツリーUID: {tree_id}")

    # Lambda入力画像をアップロード
    orig_suffix = str(uuid.uuid4())
    orig_image_key = f"{tree_id}/entire_orig_{orig_suffix}.jpg"
    try:
        await image_service.upload_image(image_data, orig_image_key)
    except Exception as e:
        logger.exception(f"画像アップロード中にエラー発生: {str(e)}")
        raise ImageUploadError(tree_id) from e

    # 画像を解析
    logger.debug("画像解析を開始")
    bucket_name = image_service.get_contents_bucket_name()
    debug_bloom_key = f"{tree_id}/entire_debug_bloom_{orig_suffix}.jpg"
    debug_noleaf_key = f"{tree_id}/entire_debug_noleaf_{orig_suffix}.jpg"

    # 非同期関数として定義
    async def run_bloom_analysis():
        return await lambda_service.analyze_tree_vitality_bloom(
            s3_bucket=bucket_name,
            s3_key=image_service.get_full_object_key(orig_image_key),
            output_bucket=bucket_name,
            output_key=image_service.get_full_object_key(debug_bloom_key)
        )

    async def run_noleaf_analysis():
        return await lambda_service.analyze_tree_vitality_noleaf(
            s3_bucket=bucket_name,
            s3_key=image_service.get_full_object_key(orig_image_key),
            output_bucket=bucket_name,
            output_key=image_service.get_full_object_key(debug_noleaf_key)
        )

    # 非同期で並列実行
    bloom_result, noleaf_result = await asyncio.gather(
        run_bloom_analysis(),
        run_noleaf_analysis()
    )

    logger.debug(f"ブルーム分析結果: {bloom_result}")
    logger.debug(f"葉なし分析結果: {noleaf_result}")

    spot = flowering_date_service.find_nearest_spot(latitude, longitude)
    if spot is None:
        logger.warning(f"最寄りの観測地点が見つかりません: ({latitude}, {longitude})")
        raise LocationNotFoundError(latitude=latitude, longitude=longitude)

    # 最寄りの観測地点から桜の元気度を推定
    target_datetime = parsed_photo_date or datetime.datetime.now()
    noleaf_weight, bloom_weight = spot.estimate_vitality(target_datetime)
    logger.debug(
        f"比率: 花なし {noleaf_weight}, 花あり {bloom_weight} (対象日時: {target_datetime})")
    final_vitality_real = noleaf_result.vitality_real * noleaf_weight + \
        bloom_result.vitality_real * bloom_weight
    final_vitality = round(final_vitality_real)

    # 人物をぼかす
    logger.debug("ぼかしを開始")
    person_labels = labels.get('Person', [])
    if len(person_labels) > 0:
        logger.debug("人物が検出されたためぼかしを適用")
        blurred_image = blur.apply_blur_to_bbox(
            image, person_labels)
        image_data = image_service.pil_to_bytes(blurred_image, 'jpeg')
        image = blurred_image

    # サムネイル作成
    logger.debug("サムネイル作成を開始")
    thumb_data = image_service.create_thumbnail(image_data)

    # 画像をアップロード
    random_suffix = str(uuid.uuid4())
    image_key = f"{tree_id}/entire_{random_suffix}.jpg"
    thumb_key = f"{tree_id}/entire_thumb_{random_suffix}.jpg"

    try:
        if not (await image_service.upload_image(image_data, image_key) and
                await image_service.upload_image(thumb_data, thumb_key)):
            logger.error(f"画像アップロード失敗: ツリーUID={tree_id}")
            raise ImageUploadError(tree_uid=tree_id)
        logger.debug(f"画像アップロード成功: image_key={image_key}")
    except Exception as e:
        logger.exception(f"画像アップロード中にエラー発生: {str(e)}")
        raise ImageUploadError(tree_uid=tree_id) from e

    # DBに登録
    try:
        repository = TreeRepository(db)
        tree = repository.create_tree(
            user_id=current_user.id,
            # uid=tree_uid,
            contributor=contributor,
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_key,
            thumb_obj_key=thumb_key,
            vitality=final_vitality,
            vitality_real=final_vitality_real,
            vitality_noleaf=noleaf_result.vitality,
            vitality_noleaf_real=noleaf_result.vitality_real,
            vitality_noleaf_weight=noleaf_weight,
            vitality_bloom=bloom_result.vitality,
            vitality_bloom_real=bloom_result.vitality_real,
            vitality_bloom_weight=bloom_weight,
            location=address.detail,
            prefecture_code=address.prefecture_code,
            municipality_code=address.municipality_code,
            block=address.block,
            photo_date=parsed_photo_date,
            debug_image_obj_key=debug_bloom_key
        )

        # デバッグモードでの自動承認
        if is_approved_debug:
            logger.info(f"デバッグモードによる自動承認: ツリーUID={tree.uid}")
            tree.censorship_status = CensorshipStatus.APPROVED
            if tree.entire_tree:
                tree.entire_tree.censorship_status = CensorshipStatus.APPROVED
            repository.update_tree(tree)

        logger.info(f"木の登録が完了: ツリーUID={tree.uid}, 元気度={bloom_result.vitality}")
    except Exception as e:
        logger.exception(f"DB登録中にエラー発生: {str(e)}")
        raise DatabaseError(message=str(e)) from e

    return TreeResponse(
        id=tree.uid,
        tree_number=f"#{tree.id}",
        contributor=filter_anonymous(contributor) if contributor else None,
        latitude=tree.latitude,
        longitude=tree.longitude,
        location=tree.location,
        prefecture_code=tree.prefecture_code,
        municipality_code=tree.municipality_code,
        vitality=bloom_result.vitality,
        created_at=tree.photo_date,
    )

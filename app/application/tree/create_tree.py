import datetime
import html
import os
import time as time_module
import uuid
from typing import Optional

from loguru import logger
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.application.exceptions import (DatabaseError,
                                        FullviewValidationError,
                                        ImageUploadError,
                                        InvalidParamError,
                                        LocationNotFoundError,
                                        LocationNotInJapanError, NgWordError,
                                        TreeNotDetectedError)
from app.domain.constants.ngwords import is_ng_word
from app.domain.models.models import CensorshipStatus, User
from app.application.tree.run_vitality_models import (
    run_vitality_models,
)
from app.domain.services.ai_service import (
    AIService,
)
from app.domain.services.flowering_date_service import FloweringDateService
from app.domain.services.fullview_validation_service import (
    FullviewValidationService,
)
from app.domain.services.image_service import ImageService
from app.domain.services.multi_stage_bloom_service import (
    MultiStageBloomService,
)
from app.infrastructure.repositories.fullview_validation_log_repository import (  # noqa: E501
    FullviewValidationLogRepository,
)
from app.domain.utils import blur
from app.domain.utils.date_utils import DateUtils
from app.infrastructure.geocoding.geocoding_service import GeocodingService
from app.infrastructure.images.label_detector import LabelDetector
from app.infrastructure.repositories.tree_repository import TreeRepository
from app.interfaces.schemas.tree import TreeResponse

STAGE = os.getenv("stage", "dev")


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
    ai_service: AIService,
    fullview_validation_service: FullviewValidationService,
    fullview_validation_log_repository: FullviewValidationLogRepository,
    multi_stage_bloom_service: MultiStageBloomService,
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
        label_detector (LabelDetector): ラベル検出器
        flowering_date_service (FloweringDateService): 桜の開花日サービス
        ai_service (AIService): AI呼び出しサービス
        fullview_validation_service: 全景バリデーションサービス
        fullview_validation_log_repository: バリデーションログリポジトリ
        multi_stage_bloom_service: 多段階開花モデルサービス
        photo_date (Optional[str]): 撮影日時（ISO8601形式）
        is_approved_debug (bool): デバッグ用に承認済みとしてマークするフラグ
        detail_debug (bool): 詳細なデバッグ情報を表示するフラグ

    Returns:
        TreeResponse: 作成された木の情報

    Raises:
        TreeNotDetectedError: 木が検出できない場合
        ImageUploadError: 画像のアップロードに失敗した場合
        DatabaseError: データベースの操作に失敗した場合
    """
    start_time_total = time_module.time()
    if contributor is not None and is_ng_word(contributor):
        raise NgWordError(contributor)

    logger.info(
        f"新しい木の登録を開始: ユーザーID={current_user.id}, 位置={latitude},{longitude}")

    # 住所情報の取得
    start_time = time_module.time()
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
    end_time = time_module.time()
    logger.info(f"住所情報の取得処理: {(end_time - start_time) * 1000:.2f}ms")

    # 日時の解析
    start_time = time_module.time()
    parsed_photo_date = None
    if photo_date:
        parsed_photo_date = DateUtils.parse_iso_date(photo_date)
        if not parsed_photo_date:
            logger.warning(f"不正な日時形式: {photo_date}")
            raise InvalidParamError(
                reason=f"不正な日時形式です: {photo_date}",
                param_name="photo_date"
            )
    end_time = time_module.time()
    logger.info(f"日時解析処理: {(end_time - start_time) * 1000:.2f}ms")

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
    labels = await label_detector.detect(image, ['Tree', 'Person'])
    print(labels)
    if "Tree" not in labels:
        logger.warning(f"Entire:木が検出できません: ユーザーID={current_user.id}")
        raise TreeNotDetectedError()
    end_time = time_module.time()
    logger.info(f"ラベル検出処理: {(end_time - start_time) * 1000:.2f}ms")

    # 全景バリデーション（既存PIL画像からリサイズしフル再展開を回避）
    start_time = time_module.time()
    _FV_MAX_EDGE = 1024
    if max(image.size) > _FV_MAX_EDGE:
        w, h = image.size
        ratio = _FV_MAX_EDGE / max(w, h)
        fv_image = image.resize(
            (int(w * ratio), int(h * ratio)),
            Image.Resampling.LANCZOS,
        )
        fv_image_bytes = image_service.pil_to_bytes(fv_image, "jpeg")
        del fv_image
    else:
        fv_image_bytes = image_data
    fv_result = await fullview_validation_service.validate(
        image_bytes=fv_image_bytes,
        image_format="jpeg",
    )
    del fv_image_bytes
    end_time = time_module.time()
    logger.info(
        "全景バリデーション処理: "
        + f"{(end_time - start_time) * 1000:.2f}ms"
    )

    if not fv_result.is_valid:
        # NG 画像を S3 に保存
        ng_date = datetime.datetime.now().strftime("%Y%m%d")
        ng_uuid = str(uuid.uuid4())
        ng_image_key = f"validation_ng/{ng_date}/{ng_uuid}.jpg"
        _ = await image_service.upload_image(
            image_data, ng_image_key
        )

        # 判定結果を DB に記録
        _ = fullview_validation_log_repository.create(
            image_obj_key=ng_image_key,
            is_valid=fv_result.is_valid,
            reason=fv_result.reason,
            confidence=fv_result.confidence,
            model_id=fullview_validation_service.model_id,
        )

        logger.warning(
            "全景バリデーション NG: "
            + f"reason={fv_result.reason}, "
            + f"confidence={fv_result.confidence:.2f}"
        )
        raise FullviewValidationError(
            reason=fv_result.reason,
            confidence=fv_result.confidence,
        )

    # UIDを生成
    tree_id = str(uuid.uuid4())
    logger.debug(f"生成されたツリーUID: {tree_id}")

    # 最寄りの観測地点を取得（モデル選択に先行して必要）
    start_time = time_module.time()
    spot = flowering_date_service.find_nearest_spot(latitude, longitude)
    if spot is None:
        logger.warning(
            "最寄りの観測地点が見つかりません: "
            + f"({latitude}, {longitude})"
        )
        raise LocationNotFoundError(
            latitude=latitude, longitude=longitude
        )
    target_datetime = parsed_photo_date or datetime.datetime.now()
    end_time = time_module.time()
    logger.info(
        "最寄りスポット取得: "
        + f"{(end_time - start_time) * 1000:.2f}ms"
    )

    # 多段階開花モデル判定 (Req 1.1-1.10, 2.2-2.4)
    start_time = time_module.time()
    photo_date_value = target_datetime.date()
    bloom_stage_result = (
        multi_stage_bloom_service.determine_bloom_stage(
            flowering_date=spot.flowering_date,
            full_bloom_date=spot.full_bloom_date,
            full_bloom_end_date=spot.full_bloom_end_date,
            prefecture_code=address.prefecture_code,
            photo_date=photo_date_value,
        )
    )
    end_time = time_module.time()
    logger.info(
        "開花段階判定: "
        + f"{(end_time - start_time) * 1000:.2f}ms"
    )

    # 画像アップロード準備
    orig_suffix = str(uuid.uuid4())
    orig_image_key = f"{tree_id}/entire_orig_{orig_suffix}.jpg"

    # フォールバック時の重み計算
    if bloom_stage_result is None:
        fb_weights = spot.estimate_vitality(target_datetime)
    else:
        fb_weights = (0.5, 0.5)

    start_time = time_module.time()
    model_result = await run_vitality_models(
        image_data=image_data,
        tree_id=tree_id,
        orig_suffix=orig_suffix,
        orig_image_key=orig_image_key,
        image_service=image_service,
        ai_service=ai_service,
        bloom_stage_result=bloom_stage_result,
        fallback_weights=fb_weights,
    )
    end_time = time_module.time()
    logger.info(
        "モデル解析処理: "
        + f"{(end_time - start_time) * 1000:.2f}ms"
    )

    final_vitality = model_result.final_vitality
    final_vitality_real = model_result.final_vitality_real
    noleaf_result_data = model_result.noleaf_result
    bloom_result_data = model_result.bloom_result
    bloom_30_result_data = model_result.bloom_30_result
    bloom_50_result_data = model_result.bloom_50_result
    noleaf_weight = model_result.noleaf_weight
    bloom_weight = model_result.bloom_weight
    bloom_30_weight = model_result.bloom_30_weight
    bloom_50_weight = model_result.bloom_50_weight
    debug_image_obj_key = model_result.debug_image_obj_key
    secondary_debug_key = model_result.debug_image_obj2_key

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
    end_time = time_module.time()
    logger.info(f"画像とサムネイルのアップロード: {(end_time - start_time) * 1000:.2f}ms")

    # DBに登録
    start_time = time_module.time()
    try:
        repository = TreeRepository(db)
        tree = repository.create_tree(
            user_id=current_user.id,
            contributor=(
                html.escape(contributor) if contributor else None
            ),
            latitude=latitude,
            longitude=longitude,
            image_obj_key=image_key,
            thumb_obj_key=thumb_key,
            vitality=final_vitality,
            vitality_real=final_vitality_real,
            vitality_noleaf=(
                noleaf_result_data.vitality
                if noleaf_result_data is not None
                else None
            ),
            vitality_noleaf_real=(
                noleaf_result_data.vitality_real
                if noleaf_result_data is not None
                else None
            ),
            vitality_noleaf_weight=noleaf_weight,
            vitality_bloom=(
                bloom_result_data.vitality
                if bloom_result_data is not None
                else None
            ),
            vitality_bloom_real=(
                bloom_result_data.vitality_real
                if bloom_result_data is not None
                else None
            ),
            vitality_bloom_weight=bloom_weight,
            vitality_bloom_30=(
                bloom_30_result_data.vitality
                if bloom_30_result_data is not None
                else None
            ),
            vitality_bloom_30_real=(
                bloom_30_result_data.vitality_real
                if bloom_30_result_data is not None
                else None
            ),
            vitality_bloom_30_weight=bloom_30_weight,
            vitality_bloom_50=(
                bloom_50_result_data.vitality
                if bloom_50_result_data is not None
                else None
            ),
            vitality_bloom_50_real=(
                bloom_50_result_data.vitality_real
                if bloom_50_result_data is not None
                else None
            ),
            vitality_bloom_50_weight=bloom_50_weight,
            location=address.detail,
            prefecture_code=address.prefecture_code,
            municipality_code=address.municipality_code,
            block=address.block,
            photo_date=parsed_photo_date,
            debug_image_obj_key=debug_image_obj_key,
            debug_image_obj2_key=secondary_debug_key,
        )

        # デバッグモードでの自動承認
        if is_approved_debug:
            logger.info(
                "デバッグモードによる自動承認: "
                + f"ツリーUID={tree.uid}"
            )
            tree.censorship_status = CensorshipStatus.APPROVED
            tree.contributor_censorship_status = CensorshipStatus.APPROVED
            if tree.entire_tree:
                tree.entire_tree.censorship_status = (
                    CensorshipStatus.APPROVED
                )
            repository.update_tree(tree)

        logger.info(
            "木の登録が完了: "
            + f"ツリーUID={tree.uid}, "
            + f"元気度={final_vitality}"
        )
    except Exception as e:
        logger.exception(f"DB登録中にエラー発生: {str(e)}")
        raise DatabaseError(message=str(e)) from e
    end_time = time_module.time()
    logger.info(f"DB登録処理: {(end_time - start_time) * 1000:.2f}ms")

    end_time_total = time_module.time()
    logger.info(
        "木の登録処理全体: "
        + f"{(end_time_total - start_time_total) * 1000:.2f}ms"
    )

    return TreeResponse(
        id=tree.uid,
        tree_number=f"#{tree.id}",
        contributor=contributor,  # 自分が作ったので.
        latitude=tree.latitude,
        longitude=tree.longitude,
        location=tree.location,
        prefecture_code=tree.prefecture_code,
        municipality_code=tree.municipality_code,
        vitality=final_vitality,
        created_at=tree.photo_date,
    )

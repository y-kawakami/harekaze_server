import asyncio
import datetime
import html
import os
import time as time_module
import uuid
from typing import Optional

from loguru import logger
from PIL import ImageOps
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
from app.domain.services.ai_service import (
    AIService,
    TreeVitalityBloom30Result,
    TreeVitalityBloom50Result,
    TreeVitalityBloomResult,
    TreeVitalityNoleafResult,
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

_VitalityResult = (
    TreeVitalityNoleafResult
    | TreeVitalityBloomResult
    | TreeVitalityBloom30Result
    | TreeVitalityBloom50Result
)


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

    # 全景バリデーション
    start_time = time_module.time()
    fv_result = await fullview_validation_service.validate(
        image_bytes=image_data,
        image_format="jpeg",
    )
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
    bucket_name = image_service.get_contents_bucket_name()

    # 各モデルの結果・重みを初期化
    noleaf_result_data: _VitalityResult | None = None
    bloom_result_data: _VitalityResult | None = None
    bloom_30_result_data: _VitalityResult | None = None
    bloom_50_result_data: _VitalityResult | None = None
    noleaf_weight: float = 0.0
    bloom_weight: float = 0.0
    bloom_30_weight: float | None = None
    bloom_50_weight: float | None = None
    debug_image_obj_key: str | None = None
    secondary_debug_key: str | None = None
    final_vitality = 0
    final_vitality_real = 0.0

    if bloom_stage_result is not None:
        # === 多段階モデルフロー (Req 3.1-3.4, 4.1-4.6) ===
        logger.info(
            "多段階モデルフロー: "
            + f"stage={bloom_stage_result.stage}, "
            + "models="
            + f"{[(m.model, m.weight) for m in bloom_stage_result.models]}"
        )

        models_needed = {
            mw.model for mw in bloom_stage_result.models
        }

        # デバッグ画像キーの生成
        debug_keys: dict[str, str] = {}
        for mt in models_needed:
            debug_keys[mt] = (
                f"{tree_id}/entire_debug_{mt}"
                + f"_{orig_suffix}.jpg"
            )

        # 画像アップロード + 必要なモデルのみ並列呼び出し
        start_time = time_module.time()

        # 各モデルのコルーチンを準備
        upload_coro = image_service.upload_image(
            image_data, orig_image_key
        )
        model_coros: dict[str, asyncio.Task[_VitalityResult]] = {}
        for mt in models_needed:
            dk = debug_keys[mt]
            full_dk = image_service.get_full_object_key(dk)
            if mt == "noleaf":
                model_coros[mt] = asyncio.ensure_future(
                    ai_service.analyze_tree_vitality_noleaf(
                        image_bytes=image_data,
                        filename="image.jpg",
                        output_bucket=bucket_name,
                        output_key=full_dk,
                    )
                )
            elif mt == "bloom_30":
                model_coros[mt] = asyncio.ensure_future(
                    ai_service.analyze_tree_vitality_bloom_30(
                        image_bytes=image_data,
                        filename="image.jpg",
                        output_bucket=bucket_name,
                        output_key=full_dk,
                    )
                )
            elif mt == "bloom_50":
                model_coros[mt] = asyncio.ensure_future(
                    ai_service.analyze_tree_vitality_bloom_50(
                        image_bytes=image_data,
                        filename="image.jpg",
                        output_bucket=bucket_name,
                        output_key=full_dk,
                    )
                )
            else:
                model_coros[mt] = asyncio.ensure_future(
                    ai_service.analyze_tree_vitality_bloom(
                        image_bytes=image_data,
                        filename="image.jpg",
                        output_bucket=bucket_name,
                        output_key=full_dk,
                    )
                )

        # アップロードとモデル呼び出しを並列実行
        model_labels = list(model_coros.keys())
        model_tasks = [model_coros[k] for k in model_labels]
        all_results = await asyncio.gather(
            upload_coro, *model_tasks
        )

        upload_result = all_results[0]
        if upload_result is False:
            logger.error("画像のアップロードに失敗しました")
            raise ImageUploadError("internal")

        # モデル結果をマッピング
        model_results: dict[str, _VitalityResult] = {}
        for i, label in enumerate(model_labels):
            r = all_results[i + 1]
            # asyncio.gather preserves order; results are vitality types
            assert isinstance(  # noqa: S101
                r,
                (
                    TreeVitalityNoleafResult,
                    TreeVitalityBloomResult,
                    TreeVitalityBloom30Result,
                    TreeVitalityBloom50Result,
                ),
            )
            model_results[label] = r

        # 重み付きブレンド計算 (Req 4.5, 4.6)
        final_vitality_real = 0.0
        for mw in bloom_stage_result.models:
            vr = model_results[mw.model].vitality_real
            final_vitality_real += vr * mw.weight
        final_vitality = max(
            1, min(5, round(final_vitality_real))
        )

        # 各モデルの weight を取得（未使用=0.0）
        weight_map = {
            mw.model: mw.weight
            for mw in bloom_stage_result.models
        }
        noleaf_weight = weight_map.get("noleaf", 0.0)
        bloom_weight = weight_map.get("bloom", 0.0)
        bloom_30_weight = weight_map.get("bloom_30", 0.0)
        bloom_50_weight = weight_map.get("bloom_50", 0.0)

        # 各モデルの結果を取得（未呼び出しは None）
        noleaf_result_data = model_results.get("noleaf")
        bloom_result_data = model_results.get("bloom")
        bloom_30_result_data = model_results.get("bloom_30")
        bloom_50_result_data = model_results.get("bloom_50")

        # デバッグ画像キーの選定（主モデルを obj_key に）
        primary_model = bloom_stage_result.models[0].model
        debug_image_obj_key = debug_keys.get(primary_model)
        if len(bloom_stage_result.models) > 1:
            sec_model = bloom_stage_result.models[1].model
            secondary_debug_key = debug_keys.get(sec_model)

        end_time = time_module.time()
        logger.info(
            "多段階モデル解析処理: "
            + f"{(end_time - start_time) * 1000:.2f}ms"
        )
        logger.info(
            "多段階モデル結果: "
            + f"stage={bloom_stage_result.stage}, "
            + f"vitality={final_vitality}, "
            + f"vitality_real={final_vitality_real:.4f}"
        )
    else:
        # === フォールバック: 従来の2モデルブレンド (Req 6.1, 6.2) ===
        logger.warning(
            "多段階判定不可のため従来の2モデルブレンドに"
            + "フォールバック"
        )

        start_time = time_module.time()
        debug_bloom_key = (
            f"{tree_id}/entire_debug_bloom_{orig_suffix}.jpg"
        )
        debug_noleaf_key = (
            f"{tree_id}/entire_debug_noleaf_{orig_suffix}.jpg"
        )

        upload_result, bloom_result_fb, noleaf_result_fb = (
            await asyncio.gather(
                image_service.upload_image(
                    image_data, orig_image_key
                ),
                ai_service.analyze_tree_vitality_bloom(
                    image_bytes=image_data,
                    filename="image.jpg",
                    output_bucket=bucket_name,
                    output_key=image_service.get_full_object_key(
                        debug_bloom_key
                    ),
                ),
                ai_service.analyze_tree_vitality_noleaf(
                    image_bytes=image_data,
                    filename="image.jpg",
                    output_bucket=bucket_name,
                    output_key=image_service.get_full_object_key(
                        debug_noleaf_key
                    ),
                ),
            )
        )

        if upload_result is False:
            logger.error("画像のアップロードに失敗しました")
            raise ImageUploadError("internal")

        noleaf_weight, bloom_weight = spot.estimate_vitality(
            target_datetime
        )
        logger.debug(
            "フォールバック比率: "
            + f"花なし {noleaf_weight}, "
            + f"花あり {bloom_weight} "
            + f"(対象日時: {target_datetime})"
        )
        final_vitality_real = (
            noleaf_result_fb.vitality_real * noleaf_weight
            + bloom_result_fb.vitality_real * bloom_weight
        )
        final_vitality = round(final_vitality_real)

        noleaf_result_data = noleaf_result_fb
        bloom_result_data = bloom_result_fb
        debug_image_obj_key = debug_bloom_key

        end_time = time_module.time()
        logger.info(
            "フォールバック解析処理: "
            + f"{(end_time - start_time) * 1000:.2f}ms"
        )

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

import datetime
import uuid
from datetime import date

from loguru import logger

from app.application.tree.run_vitality_models import (
    run_vitality_models,
)
from app.domain.constants.prefecture import PREFECTURE_CODE_MAP
from app.domain.services.ai_service import AIService
from app.domain.services.flowering_date_service import (
    FloweringDateService,
)
from app.domain.services.fullview_validation_service import (
    FullviewValidationService,
)
from app.domain.services.image_service import ImageService
from app.domain.services.multi_stage_bloom_service import (
    BloomStageResult,
    ModelWeight,
    MultiStageBloomService,
)
from app.interfaces.schemas.debug import TreeVitalityResponse
from app.interfaces.schemas.fullview_validation import (
    FullviewValidationResponse,
)


def _prefecture_name_to_code(name: str) -> str | None:
    """都道府県名からコードに変換する。

    "青森県" → "02", "北海道" → "01", "東京都" → "13" など。
    """
    # まずそのまま検索
    code = PREFECTURE_CODE_MAP.get(name)
    if code is not None:
        return code
    # サフィックス除去して検索
    for suffix in ("都", "府", "県"):
        if name.endswith(suffix):
            code = PREFECTURE_CODE_MAP.get(
                name[: -len(suffix)]
            )
            if code is not None:
                return code
    return None


_SINGLE_MODEL_STAGES: dict[str, BloomStageResult] = {
    "noleaf": BloomStageResult(
        stage="branch_only",
        models=[ModelWeight(model="noleaf", weight=1.0)],
    ),
    "bloom_30": BloomStageResult(
        stage="bloom_30",
        models=[ModelWeight(model="bloom_30", weight=1.0)],
    ),
    "bloom_50": BloomStageResult(
        stage="bloom_50",
        models=[ModelWeight(model="bloom_50", weight=1.0)],
    ),
    "bloom": BloomStageResult(
        stage="full_bloom",
        models=[ModelWeight(model="bloom", weight=1.0)],
    ),
}


async def analyze_tree_app(
    image_data: bytes,
    image_service: ImageService,
    ai_service: AIService,
    fullview_validation_service: (
        FullviewValidationService | None
    ) = None,
    mode: str = "bloom",
    latitude: float | None = None,
    longitude: float | None = None,
    photo_date: date | None = None,
    flowering_date_service: (
        FloweringDateService | None
    ) = None,
    multi_stage_bloom_service: (
        MultiStageBloomService | None
    ) = None,
) -> TreeVitalityResponse:
    """桜の木全体の写真を解析する"""
    tree_id = str(uuid.uuid4())
    orig_suffix = str(uuid.uuid4())
    orig_image_key = (
        f"{tree_id}/entire_orig_{orig_suffix}.jpg"
    )

    bloom_stage_result: BloomStageResult | None = None
    fallback_weights = (0.5, 0.5)
    bloom_stage_label: str | None = None

    if mode == "location_date":
        # 緯度経度と撮影日モード
        if (
            latitude is None or
            longitude is None or
            photo_date is None or
            flowering_date_service is None or
            multi_stage_bloom_service is None
        ):
            raise ValueError(
                "location_date モードには" +
                " latitude, longitude, photo_date," +
                " flowering_date_service," +
                " multi_stage_bloom_service が必要です"
            )

        spot = flowering_date_service.find_nearest_spot(
            latitude, longitude
        )
        if spot is None:
            raise ValueError(
                "最寄りの観測地点が見つかりません: " +
                f"({latitude}, {longitude})"
            )

        prefecture_code = _prefecture_name_to_code(
            spot.prefecture
        )

        bloom_stage_result = (
            multi_stage_bloom_service.determine_bloom_stage(
                flowering_date=spot.flowering_date,
                full_bloom_date=spot.full_bloom_date,
                full_bloom_end_date=spot.full_bloom_end_date,
                prefecture_code=prefecture_code,
                photo_date=photo_date,
            )
        )

        if bloom_stage_result is not None:
            bloom_stage_label = bloom_stage_result.stage
        else:
            # フォールバック重み計算
            target_dt = datetime.datetime(
                photo_date.year,
                photo_date.month,
                photo_date.day,
            )
            fallback_weights = spot.estimate_vitality(
                target_dt
            )

        logger.info(
            "location_date モード: " +
            f"spot={spot.address}, " +
            f"bloom_stage={bloom_stage_label}"
        )
    elif mode in _SINGLE_MODEL_STAGES:
        bloom_stage_result = _SINGLE_MODEL_STAGES[mode]
        bloom_stage_label = bloom_stage_result.stage
    else:
        raise ValueError(f"不明なモード: {mode}")

    model_result = await run_vitality_models(
        image_data=image_data,
        tree_id=tree_id,
        orig_suffix=orig_suffix,
        orig_image_key=orig_image_key,
        image_service=image_service,
        ai_service=ai_service,
        bloom_stage_result=bloom_stage_result,
        fallback_weights=fallback_weights,
    )

    # デバッグ画像URLの取得
    bloom_image_url: str | None = None
    noleaf_image_url: str | None = None
    bloom_30_image_url: str | None = None
    bloom_50_image_url: str | None = None

    for model_type, key in model_result.debug_keys.items():
        url = image_service.get_image_url(key)
        if model_type == "bloom":
            bloom_image_url = url
        elif model_type == "noleaf":
            noleaf_image_url = url
        elif model_type == "bloom_30":
            bloom_30_image_url = url
        elif model_type == "bloom_50":
            bloom_50_image_url = url

    # 全景バリデーション
    fv_response: FullviewValidationResponse | None = None
    if fullview_validation_service is not None:
        fv_result = await fullview_validation_service.validate(
            image_bytes=image_data,
            image_format="jpeg",
        )
        fv_response = FullviewValidationResponse(
            is_valid=fv_result.is_valid,
            reason=fv_result.reason,
            confidence=fv_result.confidence,
        )

    b30_w = model_result.bloom_30_weight
    b50_w = model_result.bloom_50_weight

    return TreeVitalityResponse(
        vitality=model_result.final_vitality,
        vitality_real=model_result.final_vitality_real,
        vitality_bloom=(
            model_result.bloom_result.vitality
            if model_result.bloom_result is not None
            else None
        ),
        vitality_bloom_real=(
            model_result.bloom_result.vitality_real
            if model_result.bloom_result is not None
            else None
        ),
        vitality_bloom_weight=(
            model_result.bloom_weight
            if model_result.bloom_weight > 0
            else None
        ),
        vitality_noleaf=(
            model_result.noleaf_result.vitality
            if model_result.noleaf_result is not None
            else None
        ),
        vitality_noleaf_real=(
            model_result.noleaf_result.vitality_real
            if model_result.noleaf_result is not None
            else None
        ),
        vitality_noleaf_weight=(
            model_result.noleaf_weight
            if model_result.noleaf_weight > 0
            else None
        ),
        vitality_bloom_30=(
            model_result.bloom_30_result.vitality
            if model_result.bloom_30_result is not None
            else None
        ),
        vitality_bloom_30_real=(
            model_result.bloom_30_result.vitality_real
            if model_result.bloom_30_result is not None
            else None
        ),
        vitality_bloom_30_weight=(
            b30_w
            if b30_w is not None and b30_w > 0
            else None
        ),
        vitality_bloom_50=(
            model_result.bloom_50_result.vitality
            if model_result.bloom_50_result is not None
            else None
        ),
        vitality_bloom_50_real=(
            model_result.bloom_50_result.vitality_real
            if model_result.bloom_50_result is not None
            else None
        ),
        vitality_bloom_50_weight=(
            b50_w
            if b50_w is not None and b50_w > 0
            else None
        ),
        bloom_image_url=bloom_image_url,
        noleaf_image_url=noleaf_image_url,
        bloom_30_image_url=bloom_30_image_url,
        bloom_50_image_url=bloom_50_image_url,
        bloom_stage=bloom_stage_label,
        fullview_validation=fv_response,
    )

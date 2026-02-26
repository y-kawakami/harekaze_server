"""多段階モデル解析の共通関数

create_tree.py とデバッグページの両方から呼び出される。
モデル呼び出し + ブレンド計算を一箇所にまとめる。
"""

import asyncio
from dataclasses import dataclass, field

from loguru import logger

from app.domain.services.ai_service import (
    AIService,
    TreeVitalityBloom30Result,
    TreeVitalityBloom50Result,
    TreeVitalityBloomResult,
    TreeVitalityNoleafResult,
)
from app.domain.services.image_service import ImageService
from app.domain.services.multi_stage_bloom_service import (
    BloomStageResult,
)

_VitalityResult = (
    TreeVitalityNoleafResult |
    TreeVitalityBloomResult |
    TreeVitalityBloom30Result |
    TreeVitalityBloom50Result
)


@dataclass
class VitalityModelResult:
    """多段階モデル解析の結果"""

    final_vitality: int
    final_vitality_real: float
    noleaf_result: TreeVitalityNoleafResult | None
    bloom_result: TreeVitalityBloomResult | None
    bloom_30_result: TreeVitalityBloom30Result | None
    bloom_50_result: TreeVitalityBloom50Result | None
    noleaf_weight: float
    bloom_weight: float
    bloom_30_weight: float | None
    bloom_50_weight: float | None
    debug_image_obj_key: str | None
    debug_image_obj2_key: str | None
    debug_keys: dict[str, str] = field(
        default_factory=dict
    )


async def run_vitality_models(
    image_data: bytes,
    tree_id: str,
    orig_suffix: str,
    orig_image_key: str,
    image_service: ImageService,
    ai_service: AIService,
    bloom_stage_result: BloomStageResult | None,
    fallback_weights: tuple[float, float] = (0.5, 0.5),
) -> VitalityModelResult:
    """多段階モデル解析を実行し結果を返す。

    A) bloom_stage_result が指定されている場合:
       多段階パスで必要なモデルのみ並列呼び出し。
    B) bloom_stage_result が None の場合:
       bloom + noleaf の2モデルフォールバック。
    """
    bucket_name = image_service.get_contents_bucket_name()

    if bloom_stage_result is not None:
        return await _run_multi_stage(
            image_data=image_data,
            tree_id=tree_id,
            orig_suffix=orig_suffix,
            orig_image_key=orig_image_key,
            image_service=image_service,
            ai_service=ai_service,
            bucket_name=bucket_name,
            bloom_stage_result=bloom_stage_result,
        )
    else:
        return await _run_fallback(
            image_data=image_data,
            tree_id=tree_id,
            orig_suffix=orig_suffix,
            orig_image_key=orig_image_key,
            image_service=image_service,
            ai_service=ai_service,
            bucket_name=bucket_name,
            fallback_weights=fallback_weights,
        )


async def _run_multi_stage(
    image_data: bytes,
    tree_id: str,
    orig_suffix: str,
    orig_image_key: str,
    image_service: ImageService,
    ai_service: AIService,
    bucket_name: str,
    bloom_stage_result: BloomStageResult,
) -> VitalityModelResult:
    """多段階モデルフロー"""
    from app.application.exceptions import ImageUploadError

    logger.info(
        "多段階モデルフロー: " +
        f"stage={bloom_stage_result.stage}, " +
        "models=" +
        f"{[(m.model, m.weight) for m in bloom_stage_result.models]}"
    )

    models_needed = {
        mw.model for mw in bloom_stage_result.models
    }

    # デバッグ画像キーの生成
    debug_keys: dict[str, str] = {}
    for mt in models_needed:
        debug_keys[mt] = (
            f"{tree_id}/entire_debug_{mt}" +
            f"_{orig_suffix}.jpg"
        )

    # 画像アップロード + 必要なモデルのみ並列呼び出し
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

    # 重み付きブレンド計算
    final_vitality_real = 0.0
    for mw in bloom_stage_result.models:
        vr = model_results[mw.model].vitality_real
        final_vitality_real += vr * mw.weight

    if len(bloom_stage_result.models) == 1:
        # 単一モデル: argmax をそのまま使用
        sole = model_results[bloom_stage_result.models[0].model]
        final_vitality = sole.vitality
    else:
        # 複数モデルブレンド: 期待値を丸める
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
    noleaf_res = model_results.get("noleaf")
    bloom_res = model_results.get("bloom")
    bloom_30_res = model_results.get("bloom_30")
    bloom_50_res = model_results.get("bloom_50")

    # デバッグ画像キーの選定（主モデルを obj_key に）
    primary_model = bloom_stage_result.models[0].model
    debug_image_obj_key = debug_keys.get(primary_model)
    secondary_debug_key: str | None = None
    if len(bloom_stage_result.models) > 1:
        sec_model = bloom_stage_result.models[1].model
        secondary_debug_key = debug_keys.get(sec_model)

    logger.info(
        "多段階モデル結果: " +
        f"stage={bloom_stage_result.stage}, " +
        f"vitality={final_vitality}, " +
        f"vitality_real={final_vitality_real:.4f}"
    )

    # 各結果を型安全にキャスト
    noleaf_result: TreeVitalityNoleafResult | None = None
    if isinstance(noleaf_res, TreeVitalityNoleafResult):
        noleaf_result = noleaf_res

    bloom_result: TreeVitalityBloomResult | None = None
    if isinstance(bloom_res, TreeVitalityBloomResult):
        bloom_result = bloom_res

    bloom_30_result: TreeVitalityBloom30Result | None = None
    if isinstance(bloom_30_res, TreeVitalityBloom30Result):
        bloom_30_result = bloom_30_res

    bloom_50_result: TreeVitalityBloom50Result | None = None
    if isinstance(bloom_50_res, TreeVitalityBloom50Result):
        bloom_50_result = bloom_50_res

    return VitalityModelResult(
        final_vitality=final_vitality,
        final_vitality_real=final_vitality_real,
        noleaf_result=noleaf_result,
        bloom_result=bloom_result,
        bloom_30_result=bloom_30_result,
        bloom_50_result=bloom_50_result,
        noleaf_weight=noleaf_weight,
        bloom_weight=bloom_weight,
        bloom_30_weight=bloom_30_weight,
        bloom_50_weight=bloom_50_weight,
        debug_image_obj_key=debug_image_obj_key,
        debug_image_obj2_key=secondary_debug_key,
        debug_keys=debug_keys,
    )


async def _run_fallback(
    image_data: bytes,
    tree_id: str,
    orig_suffix: str,
    orig_image_key: str,
    image_service: ImageService,
    ai_service: AIService,
    bucket_name: str,
    fallback_weights: tuple[float, float],
) -> VitalityModelResult:
    """フォールバック: 従来の2モデルブレンド"""
    from app.application.exceptions import ImageUploadError

    logger.warning(
        "多段階判定不可のため従来の2モデルブレンドに" +
        "フォールバック"
    )

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

    noleaf_weight, bloom_weight = fallback_weights
    logger.debug(
        "フォールバック比率: " +
        f"花なし {noleaf_weight}, " +
        f"花あり {bloom_weight}"
    )
    final_vitality_real = (
        noleaf_result_fb.vitality_real * noleaf_weight +
        bloom_result_fb.vitality_real * bloom_weight
    )
    final_vitality = round(final_vitality_real)

    debug_keys = {
        "bloom": debug_bloom_key,
        "noleaf": debug_noleaf_key,
    }

    return VitalityModelResult(
        final_vitality=final_vitality,
        final_vitality_real=final_vitality_real,
        noleaf_result=noleaf_result_fb,
        bloom_result=bloom_result_fb,
        bloom_30_result=None,
        bloom_50_result=None,
        noleaf_weight=noleaf_weight,
        bloom_weight=bloom_weight,
        bloom_30_weight=None,
        bloom_50_weight=None,
        debug_image_obj_key=debug_bloom_key,
        debug_image_obj2_key=None,
        debug_keys=debug_keys,
    )

import asyncio
import uuid

from loguru import logger

from app.application.exceptions import ImageUploadError
from app.domain.services.ai_service import AIService
from app.domain.services.fullview_validation_service import (
    FullviewValidationService,
)
from app.domain.services.image_service import ImageService
from app.infrastructure.images.label_detector import LabelDetector
from app.interfaces.schemas.debug import TreeVitalityResponse
from app.interfaces.schemas.fullview_validation import (
    FullviewValidationResponse,
)


async def analyze_tree_app(
    image_data: bytes,
    image_service: ImageService,
    label_detector: LabelDetector,
    ai_service: AIService,
    fullview_validation_service: FullviewValidationService | None = None,
) -> TreeVitalityResponse:
    """
    桜の木全体の写真を解析する

    Args:
        image_data: 解析対象の画像データ
        image_service: 画像サービス
        label_detector: ラベル検出サービス
        ai_service: AI呼び出しサービス

    Returns:
        TreeVitalityResponse: 木全体の解析結果
    """
    tree_id = str(uuid.uuid4())
    bucket_name = image_service.get_contents_bucket_name()

    # 画像をS3にアップロード（一時的）
    orig_suffix = str(uuid.uuid4())
    orig_image_key = f"{tree_id}/entire_orig_{orig_suffix}.jpg"
    debug_bloom_key = f"{tree_id}/entire_debug_bloom_{orig_suffix}.jpg"
    debug_noleaf_key = f"{tree_id}/entire_debug_noleaf_{orig_suffix}.jpg"

    try:
        # 画像のアップロードと解析を同時に実行
        logger.debug("画像のアップロードと解析を同時に開始")

        # 2つのタスクを並列で実行
        upload_task = image_service.upload_image(image_data, orig_image_key)

        # 開花時の解析タスク
        bloom_task = ai_service.analyze_tree_vitality_bloom(
            image_bytes=image_data,
            filename='image.jpg',
            output_bucket=bucket_name,
            output_key=image_service.get_full_object_key(debug_bloom_key)
        )

        # 葉なし時の解析タスク
        noleaf_task = ai_service.analyze_tree_vitality_noleaf(
            image_bytes=image_data,
            filename='image.jpg',
            output_bucket=bucket_name,
            output_key=image_service.get_full_object_key(debug_noleaf_key)
        )

        # 全てのタスクが完了するまで待機
        upload_result, bloom_result, noleaf_result = await asyncio.gather(
            upload_task,
            bloom_task,
            noleaf_task
        )

        if upload_result is False:
            logger.error("画像のアップロードに失敗しました")
            raise ImageUploadError('internal')

        logger.debug(f"ブルーム分析結果: {bloom_result}")
        logger.debug(f"葉なし分析結果: {noleaf_result}")

        # 現在の時期の比率を仮定（本来はflowering_date_serviceから取得）
        noleaf_weight = 0.5
        bloom_weight = 0.5

        # 総合的な活力を計算
        final_vitality_real = (noleaf_result.vitality_real * noleaf_weight +
                               bloom_result.vitality_real * bloom_weight)
        final_vitality = round(final_vitality_real)

        # 分析結果画像のURLを取得
        bloom_image_url = None
        noleaf_image_url = None

        if bloom_result.debug_image_key:
            bloom_image_url = image_service.get_image_url(
                debug_bloom_key)

        if noleaf_result.debug_image_key:
            noleaf_image_url = image_service.get_image_url(
                debug_noleaf_key)

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

        # レスポンスを作成
        return TreeVitalityResponse(
            vitality=final_vitality,
            vitality_real=final_vitality_real,
            vitality_bloom=bloom_result.vitality,
            vitality_bloom_real=bloom_result.vitality_real,
            vitality_bloom_weight=bloom_weight,
            vitality_noleaf=noleaf_result.vitality,
            vitality_noleaf_real=noleaf_result.vitality_real,
            vitality_noleaf_weight=noleaf_weight,
            bloom_image_url=bloom_image_url,
            noleaf_image_url=noleaf_image_url,
            fullview_validation=fv_response,
        )

    except Exception as e:
        logger.exception(f"木全体の解析中にエラーが発生しました: {str(e)}")
        raise e

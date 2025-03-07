import uuid

from loguru import logger
from PIL import ImageOps

from app.application.common.constants import CAN_WIDTH_MM
from app.domain.models.bounding_box import BoundingBox
from app.domain.models.tree_age import (estimate_tree_age,
                                        estimate_tree_age_from_texture)
from app.domain.services.image_service import ImageService
from app.domain.services.lambda_service import LambdaService
from app.infrastructure.images.label_detector import LabelDetector
from app.interfaces.schemas.debug import StemAnalysisResponse


async def analyze_stem_app(
    image_data: bytes,
    image_service: ImageService,
    label_detector: LabelDetector,
    lambda_service: LambdaService,
) -> StemAnalysisResponse:
    """
    幹の写真を解析する

    Args:
        image_data (bytes): 幹の写真データ
        image_service (ImageService): 画像サービス
        label_detector (LabelDetector): ラベル検出器
        lambda_service (LambdaService): Lambda呼び出しサービス

    Returns:
        StemAnalysisResponse: 解析結果
    """
    logger.info("幹の写真解析開始")

    image = image_service.bytes_to_pil(image_data)
    rotated_image = ImageOps.exif_transpose(
        image, in_place=True)  # EXIF情報に基づいて適切に回転
    if rotated_image is not None:
        image = rotated_image

    labels = label_detector.detect(image, ['Tree', 'Can'])
    if "Tree" not in labels:
        logger.warning("木が検出できません")
        return StemAnalysisResponse(
            texture=None,
            texture_real=None,
            can_detected=False,
            circumference=None,
            age=None,
            age_texture=None,
            age_circumference=None,
            analysis_image_url=None
        )

    can_bboxes = labels.get("Can", [])
    # 一番confidenceの高い缶を取得
    most_confident_can: BoundingBox | None = None
    max_confidence = 0.0
    for bbox in can_bboxes:
        if bbox.confidence > max_confidence:
            max_confidence = bbox.confidence
            most_confident_can = bbox

    # Lambda入力画像をアップロード
    orig_suffix = str(uuid.uuid4())
    orig_image_key = f"debug/stem_orig_{orig_suffix}.jpg"
    await image_service.upload_image(image_data, orig_image_key)

    # 画像の解析
    logger.debug("画像解析を開始")
    bucket_name = image_service.get_contents_bucket_name()
    debug_key = f"debug/stem_debug_{orig_suffix}.jpg"
    result = await lambda_service.analyze_stem(
        s3_bucket=bucket_name,
        s3_key=image_service.get_full_object_key(orig_image_key),
        can_bbox=most_confident_can,
        can_width_mm=CAN_WIDTH_MM,
        output_bucket=bucket_name,
        output_key=image_service.get_full_object_key(debug_key)
    )

    # 樹齢の推定
    age_texture = estimate_tree_age_from_texture(result.smoothness_real)
    age_circumference = None
    age = 0.0
    diameter = result.diameter_mm * 0.1 if result.diameter_mm else None
    if diameter:
        age_c = estimate_tree_age(diameter)
        age_circumference = round(age_c)
        age = round((age_texture + age_c) / 2)
    else:
        age = round(age_texture)

    # 解析結果画像のURL
    analysis_image_url = image_service.get_image_url(debug_key)

    return StemAnalysisResponse(
        texture=result.smoothness,
        texture_real=result.smoothness_real,
        can_detected=most_confident_can is not None,
        circumference=result.diameter_mm * 0.1 if result.diameter_mm else None,
        age=age,
        age_texture=round(age_texture),
        age_circumference=age_circumference,
        analysis_image_url=analysis_image_url
    )

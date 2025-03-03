import uuid

from loguru import logger

from app.application.exceptions import ImageUploadError
from app.domain.services.image_service import ImageService
from app.domain.utils import blur
from app.infrastructure.images.label_detector import LabelDetector
from app.interfaces.schemas.debug import BlurPrivacyResponse


def blur_privacy_app(
    image_data: bytes,
    image_service: ImageService,
    label_detector: LabelDetector,
    blur_strength: float,
) -> BlurPrivacyResponse:
    """
    桜の木全体の写真を登録する。

    Args:
        image_data (bytes): 画像データ

    Returns:
        BlurPrivacyResponse: 作成された木の情報
    """

    print(f'blur_strength: {blur_strength}')

    image = image_service.bytes_to_pil(image_data)
    labels = label_detector.detect(image, ['Tree', 'Person'])

    blurred_image = blur.apply_blur_to_bbox(
        image, labels['Person'], blur_strength=blur_strength)

    blurred_image_data = image_service.pil_to_bytes(blurred_image, 'jpeg')

    random_suffix = str(uuid.uuid4())
    image_key = f"debug/privacy/blurred_{random_suffix}.jpg"

    try:
        if not (image_service.upload_image(blurred_image_data, image_key)):
            logger.error("画像アップロード失敗")
            raise ImageUploadError()
        logger.debug("画像アップロード成功")
    except Exception as e:
        logger.exception(f"画像アップロード中にエラー発生: {str(e)}")
        raise ImageUploadError() from e

    return BlurPrivacyResponse(
        image_url=image_service.get_image_url(image_key)
    )

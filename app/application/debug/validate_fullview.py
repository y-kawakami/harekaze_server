from app.domain.services.fullview_validation_service import (
    FullviewValidationService,
)
from app.interfaces.schemas.fullview_validation import (
    FullviewValidationResponse,
)


async def validate_fullview_app(
    image_data: bytes,
    fullview_validation_service: FullviewValidationService,
) -> FullviewValidationResponse:
    """全景バリデーションのみを単独実行する

    Args:
        image_data: 画像データのバイト列
        fullview_validation_service: 全景バリデーションサービス

    Returns:
        FullviewValidationResponse: 判定結果
    """
    result = await fullview_validation_service.validate(
        image_bytes=image_data,
        image_format="jpeg",
    )

    return FullviewValidationResponse(
        is_valid=result.is_valid,
        reason=result.reason,
        confidence=result.confidence,
    )

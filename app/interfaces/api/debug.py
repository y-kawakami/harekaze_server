from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

import app.application.debug.blur_privacy
from app.domain.services.image_service import ImageService, get_image_service
from app.infrastructure.database.database import get_db
from app.infrastructure.images.label_detector import (LabelDetector,
                                                      get_label_detector)
from app.interfaces.schemas.debug import BlurPrivacyResponse

router = APIRouter()


@router.post("/debug/blur_privacy", response_model=BlurPrivacyResponse)
async def blur_privacy(
    image: UploadFile = File(
        ...,
        description="写真"
    ),
    blur_strength: float | None = Form(
        None,
        description="画像のぼかし強度(default 1.0)"
    ),
    db: Session = Depends(get_db),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
):
    """
    人物にぼかしをかける
    """
    image_data = await image.read()
    return app.application.debug.blur_privacy.blur_privacy_app(
        image_data=image_data,
        image_service=image_service,
        label_detector=label_detector,
        blur_strength=blur_strength if blur_strength is not None else 1.0,
    )

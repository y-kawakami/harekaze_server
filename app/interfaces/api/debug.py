from typing import Final

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import app.application.debug.analyze_stem
import app.application.debug.analyze_tree
import app.application.debug.blur_privacy
import app.application.debug.validate_fullview
from app.domain.services.ai_service import AIService, get_ai_service
from app.infrastructure.images.image_utils import (
    exif_transpose_bytes,
    resize_image_bytes,
)
from app.domain.services.fullview_validation_service import (
    FullviewValidationService,
    get_fullview_validation_service,
)
from app.domain.services.image_service import ImageService, get_image_service
from app.infrastructure.database.database import get_db
from app.infrastructure.images.label_detector import (LabelDetector,
                                                      get_label_detector)
from app.interfaces.api.auth_utils import get_current_username
from app.interfaces.schemas.debug import (BlurPrivacyResponse,
                                          StemAnalysisResponse,
                                          TreeVitalityResponse)
from app.interfaces.schemas.fullview_validation import (
    FullviewValidationResponse,
)

_DEBUG_MAX_LONG_EDGE: Final[int] = 2048


def _preprocess_image(
    image_data: bytes,
    max_size: int = _DEBUG_MAX_LONG_EDGE,
) -> bytes:
    """EXIF回転と長辺リサイズを行う"""
    image_data = exif_transpose_bytes(image_data)
    return resize_image_bytes(image_data, max_size)


router = APIRouter()
templates = Jinja2Templates(directory="app/interfaces/templates")


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
    image_data = _preprocess_image(image_data)
    return await app.application.debug.blur_privacy.blur_privacy_app(
        image_data=image_data,
        image_service=image_service,
        label_detector=label_detector,
        blur_strength=blur_strength if blur_strength is not None else 1.0,
    )


@router.post("/debug/analyze_stem", response_model=StemAnalysisResponse)
async def analyze_stem(
    image: UploadFile = File(
        ...,
        description="幹の写真"
    ),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
    ai_service: AIService = Depends(
        get_ai_service, use_cache=True),
):
    """
    幹の写真を解析する
    """
    image_data = await image.read()
    image_data = _preprocess_image(image_data)
    return await app.application.debug.analyze_stem.analyze_stem_app(
        image_data=image_data,
        image_service=image_service,
        label_detector=label_detector,
        ai_service=ai_service,
    )


@router.get("/debug/analyze_stem_html", response_class=HTMLResponse)
async def analyze_stem_html_get(
    request: Request,
    username: str = Depends(get_current_username),
):
    """
    幹の写真を解析するHTMLフォームを表示する
    """
    return templates.TemplateResponse(
        "stem_analysis.html",
        {"request": request, "result": None}
    )


@router.post("/debug/analyze_stem_html", response_class=HTMLResponse)
async def analyze_stem_html_post(
    request: Request,
    image: UploadFile = File(...),
    username: str = Depends(get_current_username),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
    ai_service: AIService = Depends(
        get_ai_service, use_cache=True),
):
    """
    幹の写真を解析し、結果をHTMLで表示する
    """
    try:
        image_data = await image.read()
        image_data = _preprocess_image(image_data)
        result = await app.application.debug.analyze_stem.analyze_stem_app(
            image_data=image_data,
            image_service=image_service,
            label_detector=label_detector,
            ai_service=ai_service,
        )

        return templates.TemplateResponse(
            "stem_analysis.html",
            {"request": request, "result": result}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "stem_analysis.html",
            {"request": request, "result": None,
                "error": f"エラーが発生しました: {str(e)}"}
        )


@router.post("/debug/analyze_tree", response_model=TreeVitalityResponse)
async def analyze_tree(
    image: UploadFile = File(
        ...,
        description="桜の木全体の写真"
    ),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
    ai_service: AIService = Depends(
        get_ai_service, use_cache=True),
    fullview_validation_service: FullviewValidationService = Depends(
        get_fullview_validation_service, use_cache=True),
):
    """
    桜の木全体の写真を解析する
    """
    image_data = await image.read()
    image_data = _preprocess_image(image_data)
    return await app.application.debug.analyze_tree.analyze_tree_app(
        image_data=image_data,
        image_service=image_service,
        label_detector=label_detector,
        ai_service=ai_service,
        fullview_validation_service=fullview_validation_service,
    )


@router.get("/debug/analyze_tree_html", response_class=HTMLResponse)
async def analyze_tree_html_get(
    request: Request,
    username: str = Depends(get_current_username),
):
    """
    桜の木全体の写真を解析するHTMLフォームを表示する
    """
    return templates.TemplateResponse(
        "tree_analysis.html",
        {"request": request, "result": None}
    )


@router.post("/debug/analyze_tree_html", response_class=HTMLResponse)
async def analyze_tree_html_post(
    request: Request,
    image: UploadFile = File(...),
    username: str = Depends(get_current_username),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
    ai_service: AIService = Depends(
        get_ai_service, use_cache=True),
    fullview_validation_service: FullviewValidationService = Depends(
        get_fullview_validation_service, use_cache=True),
):
    """
    桜の木全体の写真を解析し、結果をHTMLで表示する
    """
    try:
        image_data = await image.read()
        image_data = _preprocess_image(image_data)
        result = await app.application.debug.analyze_tree.analyze_tree_app(
            image_data=image_data,
            image_service=image_service,
            label_detector=label_detector,
            ai_service=ai_service,
            fullview_validation_service=fullview_validation_service,
        )

        return templates.TemplateResponse(
            "tree_analysis.html",
            {"request": request, "result": result}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "tree_analysis.html",
            {"request": request, "result": None,
                "error": f"エラーが発生しました: {str(e)}"}
        )


@router.post(
    "/debug/validate_fullview",
    response_model=FullviewValidationResponse,
)
async def validate_fullview(
    image: UploadFile = File(
        ...,
        description="桜の写真"
    ),
    fullview_validation_service: FullviewValidationService = Depends(
        get_fullview_validation_service, use_cache=True),
):
    """
    全景バリデーションのみを実行する
    """
    image_data = await image.read()
    image_data = _preprocess_image(image_data)
    return await app.application.debug.validate_fullview.validate_fullview_app(
        image_data=image_data,
        fullview_validation_service=fullview_validation_service,
    )


@router.get(
    "/debug/validate_fullview_html",
    response_class=HTMLResponse,
)
async def validate_fullview_html_get(
    request: Request,
    username: str = Depends(get_current_username),
):
    """
    全景バリデーション専用デバッグページを表示する
    """
    return templates.TemplateResponse(
        "fullview_validation.html",
        {"request": request, "result": None}
    )


@router.post(
    "/debug/validate_fullview_html",
    response_class=HTMLResponse,
)
async def validate_fullview_html_post(
    request: Request,
    image: UploadFile = File(...),
    username: str = Depends(get_current_username),
    fullview_validation_service: FullviewValidationService = Depends(
        get_fullview_validation_service, use_cache=True),
):
    """
    全景バリデーションを実行し、結果をHTMLで表示する
    """
    try:
        image_data = await image.read()
        image_data = _preprocess_image(image_data)
        result = (
            await app.application.debug.validate_fullview
            .validate_fullview_app(
                image_data=image_data,
                fullview_validation_service=fullview_validation_service,
            )
        )

        return templates.TemplateResponse(
            "fullview_validation.html",
            {"request": request, "result": result}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "fullview_validation.html",
            {"request": request, "result": None,
                "error": f"エラーが発生しました: {str(e)}"}
        )


@router.get("/debug/blur_privacy_html", response_class=HTMLResponse)
async def blur_privacy_html_get(
    request: Request,
    username: str = Depends(get_current_username),
):
    """
    人物ぼかしデバッグページを表示する
    """
    return templates.TemplateResponse(
        "blur_privacy.html",
        {"request": request, "blur_strength": "1.0"}
    )


@router.post("/debug/blur_privacy_html", response_class=HTMLResponse)
async def blur_privacy_html_post(
    request: Request,
    image: UploadFile = File(...),
    blur_strength: float = Form(1.0),
    username: str = Depends(get_current_username),
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
):
    """
    人物ぼかし処理を行い、結果をHTMLで表示する
    """
    try:
        image_data = await image.read()
        image_data = _preprocess_image(image_data)
        result = await app.application.debug.blur_privacy.blur_privacy_app(
            image_data=image_data,
            image_service=image_service,
            label_detector=label_detector,
            blur_strength=blur_strength,
        )

        return templates.TemplateResponse(
            "blur_privacy.html",
            {"request": request, "result": result,
                "blur_strength": str(blur_strength)}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "blur_privacy.html",
            {"request": request, "result": None,
                "blur_strength": str(blur_strength),
                "error": f"エラーが発生しました: {str(e)}"}
        )

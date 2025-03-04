from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import app.application.debug.analyze_stem
import app.application.debug.analyze_tree
import app.application.debug.blur_privacy
from app.domain.services.image_service import ImageService, get_image_service
from app.domain.services.lambda_service import (LambdaService,
                                                get_lambda_service)
from app.infrastructure.database.database import get_db
from app.infrastructure.images.label_detector import (LabelDetector,
                                                      get_label_detector)
from app.interfaces.schemas.debug import (BlurPrivacyResponse,
                                          StemAnalysisResponse,
                                          TreeVitalityResponse)

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
    return app.application.debug.blur_privacy.blur_privacy_app(
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
    lambda_service: LambdaService = Depends(
        get_lambda_service, use_cache=True),
):
    """
    幹の写真を解析する
    """
    image_data = await image.read()
    return await app.application.debug.analyze_stem.analyze_stem_app(
        image_data=image_data,
        image_service=image_service,
        label_detector=label_detector,
        lambda_service=lambda_service,
    )


@router.get("/debug/analyze_stem_html", response_class=HTMLResponse)
async def analyze_stem_html_get(
    request: Request,
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
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
    lambda_service: LambdaService = Depends(
        get_lambda_service, use_cache=True),
):
    """
    幹の写真を解析し、結果をHTMLで表示する
    """
    try:
        image_data = await image.read()
        result = await app.application.debug.analyze_stem.analyze_stem_app(
            image_data=image_data,
            image_service=image_service,
            label_detector=label_detector,
            lambda_service=lambda_service,
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
    lambda_service: LambdaService = Depends(
        get_lambda_service, use_cache=True),
):
    """
    桜の木全体の写真を解析する
    """
    image_data = await image.read()
    return await app.application.debug.analyze_tree.analyze_tree_app(
        image_data=image_data,
        image_service=image_service,
        label_detector=label_detector,
        lambda_service=lambda_service,
    )


@router.get("/debug/analyze_tree_html", response_class=HTMLResponse)
async def analyze_tree_html_get(
    request: Request,
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
    image_service: ImageService = Depends(get_image_service, use_cache=True),
    label_detector: LabelDetector = Depends(
        get_label_detector, use_cache=True),
    lambda_service: LambdaService = Depends(
        get_lambda_service, use_cache=True),
):
    """
    桜の木全体の写真を解析し、結果をHTMLで表示する
    """
    try:
        image_data = await image.read()
        result = await app.application.debug.analyze_tree.analyze_tree_app(
            image_data=image_data,
            image_service=image_service,
            label_detector=label_detector,
            lambda_service=lambda_service,
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

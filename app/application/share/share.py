"""シェア機能のアプリケーションロジック"""
import os

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.domain.services.image_service import ImageService
from app.infrastructure.repositories.tree_repository import TreeRepository

APP_HOST = os.getenv("APP_HOST", "localhost")


def create_share_response(
    request: Request,
    tree_id: str,
    share_type: int,
    db: Session,
    image_service: ImageService,
    templates: Jinja2Templates,
    og_url: str = "https://harekaze.kirin.co.jp/sakura_camera/",
    redirect_url: str = "https://harekaze.kirin.co.jp/sakura_camera/"
) -> HTMLResponse:
    """
    シェア用のHTMLレスポンスを生成する

    Args:
        request: リクエスト情報
        tree_id: 木のID
        share_type: シェアタイプ (1=木全体, 2=幹)
        db: データベースセッション
        image_service: 画像サービス
        templates: テンプレートエンジン
        og_url: OGPに設定するURL
        redirect_url: リダイレクト先のURL

    Returns:
        HTMLResponse: シェア用HTMLレスポンス
    """

    og_url = APP_HOST + "/sakura_camera/"
    redirect_url = APP_HOST + "/sakura_camera/"

    tree_repo = TreeRepository(db)

    # シェアタイプに応じたテンプレートを選択
    if share_type == 1:
        template_name = "share_entire_tree.html"
        tree = tree_repo.get_tree_with_entire_tree(tree_id)
        if not tree:
            raise HTTPException(status_code=404, detail="Tree not found")
        entire_tree = tree.entire_tree
        if not entire_tree:
            raise HTTPException(status_code=404, detail="EntireTree not found")
        if not entire_tree.ogp_image_obj_key:
            raise HTTPException(status_code=404, detail="OGP image not found")
        image_url = image_service.get_image_url(entire_tree.ogp_image_obj_key)
    elif share_type == 2:
        template_name = "share_stem.html"
        tree = tree_repo.get_tree_with_stem(tree_id)
        if not tree:
            raise HTTPException(status_code=404, detail="Tree not found")
        stem = tree.stem
        if not stem:
            raise HTTPException(status_code=404, detail="Stem not found")
        if not stem.ogp_image_obj_key:
            raise HTTPException(status_code=404, detail="OGP image not found")
        image_url = image_service.get_image_url(stem.ogp_image_obj_key)
    else:
        raise HTTPException(status_code=400, detail="Invalid share type")

    # テンプレートにデータを渡してHTMLを生成
    context = {
        "request": request,
        "tree_id": tree_id,
        "image_url": image_url,
        "share_type": share_type,
        "og_url": og_url,
        "redirect_url": redirect_url
    }

    return templates.TemplateResponse(template_name, context)

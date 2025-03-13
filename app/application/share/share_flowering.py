"""シェア機能のアプリケーションロジック"""
import os

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

APP_HOST = os.getenv("APP_HOST", "localhost")


def create_share_flowering_response(
    request: Request,
    id: str,
    updated: str,
    templates: Jinja2Templates,
    og_url: str = "https://harekaze.kirin.co.jp/sakura_camera/",
    redirect_url: str = "https://harekaze.kirin.co.jp/sakura_camera/"
) -> HTMLResponse:
    """
    シェア用のHTMLレスポンスを生成する

    Args:
        request: リクエスト情報
        id: 地点ID
        updated: 更新日時
        templates: テンプレートエンジン
        og_url: OGPに設定するURL
        redirect_url: リダイレクト先のURL

    Returns:
        HTMLResponse: シェア用HTMLレスポンス
    """

    og_url = APP_HOST + "/sakura_camera/"
    redirect_url = APP_HOST + "/sakura_camera/"
    image_url = APP_HOST + f"/sakura_camera/flowering_image/{updated}/{id}.png"

    template_name = "share_flowering.html"

    # テンプレートにデータを渡してHTMLを生成
    context = {
        "request": request,
        "image_url": image_url,
        "og_url": og_url,
        "redirect_url": redirect_url
    }

    return templates.TemplateResponse(template_name, context)

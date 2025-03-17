import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic
from starlette.middleware.base import BaseHTTPMiddleware

from app.interfaces.api import (admin_auth, admin_censorship, auth, debug,
                                info, ping, tree)
from app.interfaces.api.auth_utils import get_current_username
from app.interfaces.api.error_handlers import register_error_handlers
from app.interfaces.share import share

load_dotenv()
STAGE = os.getenv("stage", "dev")


security = HTTPBasic()


def swagger_ui_auth(username: str = Depends(get_current_username)):
    return username


# セキュリティヘッダーを追加するミドルウェア
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"

        # キャッシュ制御ヘッダーの追加
        if request.method == "GET" and request.url.path.startswith("/sakura_camera/api/"):
            # キャッシュを許可する情報取得系のエンドポイント
            cacheable_endpoints = [
                "/sakura_camera/api/tree/search",
                "/sakura_camera/api/tree/total_count",
                "/sakura_camera/api/tree/area_count",
                "/sakura_camera/api/tree/area_stats",
                "/sakura_camera/api/tree/time_block",
                "/sakura_camera/api/info/flowering_date"
            ]

            # 動的なID部分を持つエンドポイント（例: /tree/{tree_id}）
            tree_detail_pattern = "/sakura_camera/api/tree/"

            if any(request.url.path.startswith(endpoint) for endpoint in cacheable_endpoints) or (
                request.url.path.startswith(tree_detail_pattern) and
                # /sakura_camera/api/tree/{tree_id} の形式
                len(request.url.path.split("/")) == 5
            ):
                # GETリクエストに対して10分間のキャッシュを許可
                response.headers["Cache-Control"] = "public, max-age=300"
            else:
                # その他のGETリクエストはキャッシュなし
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

        elif request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # 変更を行うメソッドに対してはキャッシュを無効化
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response


app = FastAPI(
    title="晴れ風API",
    description="""
    桜の木の情報を管理するためのAPI。

    ## 主な機能

    * 桜の木の写真登録と状態診断
    * 幹の写真登録と樹齢推定
    * 桜の木の状態（穴、テングス病、キノコ）の記録
    * 地域ごとの桜の木の検索と統計情報の取得
    """,
    version="1.0.0",
    docs_url=None,  # 一旦無効化
    openapi_url="/sakura_camera/api/openapi.json",
    contact={
        "name": "開発チーム",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "auth",
            "description": "認証に関するエンドポイント."
        },
        {
            "name": "tree",
            "description": "桜の木情報に関するエンドポイント."
        },
        {
            "name": "info",
            "description": "その他の情報取得に関するエンドポイント."
        }
    ]
)

# エラーハンドラの登録
register_error_handlers(app)

# セキュリティヘッダーミドルウェアの追加
app.add_middleware(SecurityHeadersMiddleware)

if STAGE == "dev":
    # CORS設定
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r'.*',  # すべてのドメインを許可（セキュリティ上非推奨）
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # CORS設定
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://kb6rvv06ctr2.com"
        ],  # 以下のドメインを許可していた
        # allow_origins=[
        #     "https://develop.d2t1gkpzg4f6i0.amplifyapp.com",
        #     "https://release-dev-inner.d2t1gkpzg4f6i0.amplifyapp.com",
        #     "http://localhost:3000",
        #     "http://localhost:8000",
        #     "http://localhost:8080"
        #     "https://localhost:3000",
        #     "https://localhost:8000",
        #     "https://localhost:8080"
        # ],
        # allow_origin_regex=r'.*',  # すべてのドメインを許可（セキュリティ上非推奨）
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ルーターの登録
app.include_router(auth.router, prefix="/sakura_camera/api", tags=["auth"])
app.include_router(tree.router, prefix="/sakura_camera/api", tags=["tree"])
app.include_router(info.router, prefix="/sakura_camera/api", tags=["info"])
app.include_router(ping.router, prefix="/sakura_camera/api", tags=["ping"])
app.include_router(debug.router, prefix="/sakura_camera/api", tags=["debug"])
app.include_router(share.router, prefix="/sakura_camera", tags=["share"])
app.include_router(admin_auth.router, prefix="/admin_api", tags=["admin"])
app.include_router(admin_censorship.router,
                   prefix="/admin_api", tags=["admin"])

# カスタムSwagger UIエンドポイントを追加


@app.get("/sakura_camera/api/docs", dependencies=[Depends(get_current_username)])
async def custom_swagger_ui():
    from fastapi.openapi.docs import get_swagger_ui_html
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url if app.openapi_url else "/sakura_camera/api/openapi.json",
        title="晴れ風API - Swagger UI"
    )
    # SwaggerUIはキャッシュしない
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

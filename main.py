import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.interfaces.api import auth, debug, info, ping, tree
from app.interfaces.api.error_handlers import register_error_handlers

load_dotenv()

security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(
        credentials.username, os.getenv("SWAGGER_USERNAME", "harekaze"))
    correct_password = secrets.compare_digest(
        credentials.password, os.getenv("SWAGGER_PASSWORD", "hrkz2025"))
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証に失敗しました",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def swagger_ui_auth(username: str = Depends(get_current_username)):
    return username


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

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # 以下のドメインを許可していた
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
    allow_origin_regex=r'.*',  # すべてのドメインを許可（セキュリティ上非推奨）
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

# カスタムSwagger UIエンドポイントを追加


@app.get("/sakura_camera/api/docs", dependencies=[Depends(get_current_username)])
async def custom_swagger_ui():
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(
        openapi_url=app.openapi_url if app.openapi_url else "/sakura_camera/api/openapi.json",
        title="晴れ風API - Swagger UI"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

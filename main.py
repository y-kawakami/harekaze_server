from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.interfaces.api import auth, info, tree

app = FastAPI(
    title="晴れ風API",
    description="""
    桜の木の情報を管理するためのAPI。

    ## 主な機能

    * 桜の木の写真登録と状態診断
    * 幹の写真登録と樹齢推定
    * 桜の木の状態（穴、テングス病、キノコ）の記録
    * 地域ごとの桜の木の検索と統計情報の取得

    ## 認証

    * APIの利用にはセッショントークンが必要です
    * セッショントークンは `/api/auth/session` エンドポイントで取得できます
    """,
    version="1.0.0",
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

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://develop.d2t1gkpzg4f6i0.amplifyapp.com",
        "https://release-dev-inner.d2t1gkpzg4f6i0.amplifyapp.com",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080"
        "https://localhost:3000",
        "https://localhost:8000",
        "https://localhost:8080"],  # 本番環境では適切に制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(tree.router, prefix="/api", tags=["tree"])
app.include_router(info.router, prefix="/api", tags=["info"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

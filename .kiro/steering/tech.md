# Technology Stack

## Architecture

レイヤードアーキテクチャ（Clean Architecture風）を採用。外部依存を内側の層から分離し、ビジネスロジックをドメイン層に集約。

## Core Technologies

- **Language**: Python 3.12
- **Framework**: FastAPI 0.115
- **ORM**: SQLAlchemy 2.0 (Mapped型アノテーション)
- **Database**: MySQL 8.0 + GeoAlchemy2 (空間データ)
- **Migration**: Alembic

## Key Libraries

- **AWS連携**: boto3, aioboto3 (S3, Lambda, Rekognition)
- **画像処理**: Pillow, OpenCV
- **認証**: python-jose (JWT), passlib/bcrypt
- **ジオコーディング**: googlemaps
- **ロギング**: loguru
- **バリデーション**: Pydantic 2.x

## Development Standards

### Type Safety
- SQLAlchemy Mapped型を使用した明示的な型定義
- Pydantic モデルによるリクエスト/レスポンス検証

### Code Quality
- asyncキーワードによる非同期処理
- 依存性注入パターン（FastAPI Depends）

### Testing
- pytest + pytest-asyncio
- httpx によるAPIテスト
- 層ごとのテスト分離（domain/application/infrastructure/interfaces）

## Development Environment

### Required Tools
- Python 3.12+
- uv (パッケージマネージャー)
- MySQL 8.0+

### Common Commands
```bash
# Dev: gunicorn main:app --worker-class uvicorn.workers.UvicornWorker --reload --bind 0.0.0.0:8000
# Test: pytest
# Migration: alembic upgrade head
```

## Key Technical Decisions

- **画像保存**: S3直接アップロード、Lambda経由でAI解析
- **空間検索**: PostGIS互換のGeoAlchemy2によるPOINTジオメトリ
- **検閲ワークフロー**: IntEnum (CensorshipStatus) による状態管理
- **キャッシュ戦略**: GETエンドポイントに対して Cache-Control ヘッダー付与

---
_Document standards and patterns, not every dependency_

# Project Structure

## Organization Philosophy

レイヤードアーキテクチャを採用。各層は明確な責務を持ち、依存関係は外側から内側への一方向のみ許可。

```
interfaces → application → domain ← infrastructure
```

## Directory Patterns

### Domain Layer (`/app/domain/`)
**Purpose**: ビジネスロジック、エンティティ、ドメインサービス
**Contents**:
- `models/`: SQLAlchemyモデル定義（Tree, Stem, EntireTree等）
- `services/`: ドメインサービス（AIService, ImageService, BloomStateService, FloweringDateService, LambdaService, MunicipalityService等）
- `constants/`: 定数定義（都道府県コード、NGワード等）
- `utils/`: ドメイン固有ユーティリティ

### Application Layer (`/app/application/`)
**Purpose**: ユースケース実装、オーケストレーション
**Pattern**: 機能ドメインごとのサブディレクトリ
- `tree/`: 木の登録・検索関連（create_tree, search_trees等）
- `admin/`: 管理機能（検閲、一覧取得等）
- `annotation/`: アノテーション機能（注釈、CSV出力等）
- `info/`: 情報取得（開花日等）
- `common/`: 共通ユーティリティ（ぼかし処理、定数等）
- `share/`: シェア機能
- `debug/`: デバッグ用エンドポイント

### Infrastructure Layer (`/app/infrastructure/`)
**Purpose**: 外部サービス連携、データアクセス実装
- `database/`: DB接続、セッション管理
- `repositories/`: リポジトリパターン実装
- `geocoding/`: Google Maps API連携
- `images/`: AWS Rekognition連携

### Tools (`/app/tools/`)
**Purpose**: 画像処理等の低レベルツール
- `face_analyzer.py`: OpenCVによる顔検出・ぼかし処理

### Interfaces Layer (`/app/interfaces/`)
**Purpose**: 外部とのインターフェース定義
- `api/`: FastAPIルーター（エンドポイント定義）
  - 認証は機能別に分離: `auth.py`（一般）、`admin_auth.py`（管理者）、`annotation_auth.py`（アノテーター）
  - `error_handlers.py`: グローバルエラーハンドリング
  - `ping.py`: ヘルスチェックエンドポイント
- `schemas/`: Pydanticスキーマ（リクエスト/レスポンス）
- `share/`: シェアページ用テンプレート
- `templates/`: Jinja2 HTMLテンプレート

## Naming Conventions

- **Files**: snake_case (`create_tree.py`, `tree_repository.py`)
- **Classes**: PascalCase (`TreeRepository`, `AIService`)
- **Functions**: snake_case (`get_tree_detail`, `create_stem_app`)
- **Constants**: UPPER_SNAKE_CASE (`APPROVED_DEBUG`)

## Import Organization

```python
# Standard library
from datetime import datetime
from typing import Optional

# Third-party
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# Local - absolute imports from app root
from app.domain.models.models import Tree
from app.application.tree.create_tree import create_tree as create_tree_app
from app.infrastructure.database.database import get_db
```

**Path Pattern**: `from app.<layer>.<module>.<file> import <symbol>`

## Code Organization Principles

- **エンドポイント**: `interfaces/api/` で定義、ビジネスロジックは `application/` に委譲
- **依存性注入**: FastAPI `Depends` でサービス・リポジトリを注入
- **ファクトリ関数**: `get_<service>()` パターンでインスタンス生成
- **テスト**: 本番コードと同じ層構造を `tests/` に反映

## Deployment Structure

Docker経由で3つの独立サービスとしてデプロイ（`/Docker/`）:
- `Dockerfile.appapi` / `Dockerfile.adminapi` / `Dockerfile.annotationapi`
- `build-to-ecr.sh` でECRへプッシュ

## Supporting Directories

- `/scripts/`: デプロイ・管理スクリプト（deploy_*.sh, create_admin.py等）
- `/master/`: マスターデータ（CSV/JSON）
- `/query/`: SQL分析クエリ
- `/alembic/`: DBマイグレーション

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_
_updated_at: 2026-02-06_

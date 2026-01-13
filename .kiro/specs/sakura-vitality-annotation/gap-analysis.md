# ギャップ分析レポート: sakura-vitality-annotation

## 1. 分析サマリー

### 概要
桜の元気度アノテーションツールは、既存のHarekazeScan APIサーバーに新しいWebベースのアノテーション機能を追加する要件です。

### 主要な発見事項
- **既存資産の活用**: 認証基盤（Admin/JWT）、S3連携、データモデル（EntireTree）が再利用可能
- **新規作成が必要**: アノテーション結果テーブル、アノテーター認証、Web UI（一覧・詳細画面）
- **統合の複雑さ**: 中程度 - 既存パターンに沿った拡張で対応可能
- **開花予想日データ**: CSVからの読み込みサービスが既存で利用可能

### 推奨アプローチ
**Option C（ハイブリッド）** を推奨。既存の認証・S3サービスを拡張しつつ、アノテーション機能は新規コンポーネントとして実装。

---

## 2. 現状調査

### 2.1 関連する既存資産

#### データモデル（`app/domain/models/models.py`）
| モデル | 用途 | 再利用可能性 |
|--------|------|-------------|
| `EntireTree` | 桜全体画像情報（image_obj_key, vitality, tree_id等） | 参照のみ（読み取り）|
| `Tree` | ユーザ情報、撮影場所、prefecture_code | 参照のみ（読み取り）|
| `Admin` | 管理者認証（username, hashed_password） | パターンの参考として再利用 |

#### 認証サービス（`app/domain/services/auth_service.py`）
- **JWT認証**: `create_admin_token()`, `verify_admin_token()` が実装済み
- **パスワードハッシュ**: bcrypt + passlib による安全なハッシュ化
- **セッション管理**: 30日間有効なアクセストークン

#### S3画像サービス（`app/domain/services/image_service.py`）
- **バケット**: 環境変数 `S3_CONTENTS_BUCKET` から取得（要件の `hrkz-prd-s3-contents` と一致確認要）
- **画像プレフィックス**: `sakura_camera/media/trees`（既存コードと一致）
- **署名付きURL**: `get_presigned_url()` で1時間有効なURLを生成可能

#### 開花予想日サービス（`app/domain/services/flowering_date_service.py`）
- **データソース**: `master/flowering_date.csv` から読み込み
- **提供情報**: 開花予想日、満開開始予想日、満開終了予想日、都道府県、住所
- **検索機能**: `find_nearest_spot()` で緯度経度から最寄りの予想地点を取得可能

#### APIルーター構造（`main.py`）
```
/sakura_camera/api/* - 一般API
/admin_api/*          - 管理者API（認証、検閲）
```

### 2.2 アーキテクチャパターン

```
app/
├── domain/
│   ├── models/         # SQLAlchemy モデル
│   └── services/       # ドメインサービス（シングルトンパターン）
├── application/        # ユースケース実装
├── infrastructure/
│   ├── database/       # DB接続（get_db依存関数）
│   └── repositories/   # リポジトリパターン
└── interfaces/
    ├── api/            # FastAPIルーター
    ├── schemas/        # Pydanticスキーマ
    └── templates/      # Jinja2テンプレート（既存：シェアページ用）
```

---

## 3. 要件との対応分析

### 3.1 要件-資産マッピング

| 要件 | 既存資産 | ギャップ | 状態 |
|------|----------|----------|------|
| Req 1: アノテーター認証 | `Admin` モデル, `AuthService` | 新規テーブル（annotators）、専用認証ロジック | **新規作成** |
| Req 2: 桜一覧表示 | `EntireTree`, `Tree`, `ImageService` | 一覧取得ロジック、Web UI | **新規作成** |
| Req 3: 一覧フィルタリング | `TreeRepository` のフィルタリングパターン | アノテーション状態フィルタ、元気度フィルタ | **新規作成** |
| Req 4: アノテーション入力 | - | 入力フォーム、保存ロジック、結果テーブル | **新規作成** |
| Req 5: 撮影情報表示 | `FloweringDateService`, `Tree` | UI統合 | **拡張** |
| Req 6: ナビゲーション | - | 前後移動ロジック | **新規作成** |
| Req 7: DB設計 | `database.py` 接続パターン | 2テーブル追加（annotations, annotators） | **新規作成** |
| Req 8: S3画像連携 | `ImageService` | バケット名/パス確認、サムネイル表示 | **拡張** |

### 3.2 特定されたギャップ

#### 3.2.1 Missing（欠落している機能）

1. **アノテーション結果テーブル**
   - entire_tree_id（FK）、元気度値（1-5, -1）、アノテーション日時、アノテーターID
   - Alembicマイグレーションの作成が必要

2. **アノテーターテーブル**
   - ユーザID（username）、パスワード（hashed_password）
   - `Admin` テーブルと類似構造だが別テーブルとして管理

3. **Web UI（React + TypeScript + Tailwind CSS）**
   - 一覧画面（サムネイル、フィルター、件数表示）
   - アノテーション画面（画像表示、入力フォーム、ナビゲーション）
   - ログイン画面
   - **技術: React + TypeScript + Tailwind CSS**（バックエンドはREST API提供）

4. **アノテーション専用リポジトリ・サービス**
   - アノテーション結果のCRUD
   - フィルタリング・カウント集計

#### 3.2.2 Unknown（要調査事項）

1. ~~**S3パスの確認**~~ **解決済み**
   - 正しいパス: `sakura_camera/media/trees`
   - 既存コードと一致することを確認

2. **DBユーザー/DB名**
   - 既存: 環境変数から `DB_USER`, `DB_NAME` を取得
   - 要件: `hrkz_user`, `hrkz_db` を指定
   - **→ 環境変数設定で対応可能（制約なし）**

3. ~~**フロントエンド技術選定**~~ **解決済み**
   - **React + TypeScript + Tailwind CSS** で実装
   - バックエンドはREST API提供のみ

#### 3.2.3 Constraint（制約事項）

1. **認証の分離**
   - 既存 `Admin` とは別のアノテーター認証が必要
   - JWTのペイロードに `is_annotator` フラグを追加して区別

2. **データ整合性**
   - `entire_trees` テーブルへの書き込みは行わない（元気度は別テーブルに保存）
   - 既存の `vitality` カラムとアノテーション結果は独立して管理

---

## 4. 実装アプローチの選択肢

### Option A: 既存コンポーネントの拡張

**概要**: `Admin` モデルと `AuthService` を拡張してアノテーター機能を追加

**対象ファイル**:
- `app/domain/models/models.py` - Annotator, Annotationモデル追加
- `app/domain/services/auth_service.py` - アノテーター認証メソッド追加
- `app/interfaces/api/admin_auth.py` - アノテーターログインエンドポイント追加

**トレードオフ**:
- ✅ コード量が少ない
- ✅ 既存の認証フローを再利用
- ❌ Adminとの責務混在リスク
- ❌ 将来的な機能分離が困難

### Option B: 新規コンポーネントとして作成

**概要**: アノテーション機能を完全に独立したモジュールとして実装

**新規作成**:
```
app/
├── domain/
│   ├── models/annotation.py       # Annotator, Annotationモデル
│   └── services/annotation_service.py
├── application/annotation/
│   ├── annotate_tree.py
│   ├── get_annotation_list.py
│   └── get_annotation_detail.py
├── infrastructure/repositories/
│   └── annotation_repository.py
└── interfaces/
    ├── api/annotation.py
    ├── api/annotation_auth.py
    └── schemas/annotation.py
```

**トレードオフ**:
- ✅ 責務が明確に分離
- ✅ テストが容易
- ✅ 将来の拡張に対応しやすい
- ❌ ファイル数が多い
- ❌ 共通処理の重複の可能性

### Option C: ハイブリッドアプローチ（推奨）

**概要**: 認証サービスは既存を拡張、アノテーション機能は新規モジュール

**実装方針**:
1. **認証**: `AuthService` にアノテーター用メソッドを追加（既存パターン踏襲）
2. **モデル**: `models.py` に `Annotator`, `VitalityAnnotation` を追加
3. **ビジネスロジック**: `app/application/annotation/` に新規作成
4. **API**: `/annotation_api/*` プレフィックスで新規ルーター
5. **UI**: `app/interfaces/templates/annotation/` にJinja2テンプレート

**トレードオフ**:
- ✅ 認証の一貫性を保持
- ✅ アノテーション機能は独立してテスト可能
- ✅ 適度なコード量
- ❌ 一部で責務の境界があいまい

---

## 5. 複雑さとリスク評価

### 工数見積もり: **M（中規模）**

| カテゴリ | 工数 | 根拠 |
|----------|------|------|
| DBモデル・マイグレーション | S | 2テーブル追加、既存パターン踏襲 |
| 認証機能 | S | 既存 `AuthService` の拡張 |
| API実装 | M | 一覧/詳細/保存/フィルタリング |
| Web UI | M | 2画面（Jinja2の場合）|
| 統合・テスト | S | 既存テストパターンに従う |

### リスク評価: **Low～Medium**

| リスク | 影響度 | 緩和策 |
|--------|--------|--------|
| S3パス不一致 | 中 | 設計フェーズで実際のS3構造を確認 |
| 認証の複雑化 | 低 | JWTペイロードで明確に区別 |
| パフォーマンス | 低 | 一覧のページネーション、サムネイルURL生成の最適化 |
| UI実装 | 中 | Jinja2 or 別フロントエンドの早期決定 |

---

## 6. 設計フェーズへの申し送り事項

### 要調査項目（すべて解決済み）
1. [x] ~~S3バケット名とパスの実環境確認~~ → `sakura_camera/media/trees` で確定
2. [x] ~~フロントエンド技術選定~~ → **React + TypeScript + Tailwind CSS** で確定
3. [x] ~~アノテーター初期登録の運用フロー~~ → **DBに手動登録**（登録UIは不要）

### 設計時の検討事項
1. アノテーション結果の重複登録防止（UNIQUE制約 or UPDATE）
2. 開花予想日データの取得方法（Tree位置からの逆引き）
3. ナビゲーション時のフィルター状態維持
4. サムネイル画像のサイズ・キャッシュ戦略

### 推奨アーキテクチャ
- **認証**: 既存 `AuthService` を拡張
- **データ**: `models.py` に2モデル追加 + Alembicマイグレーション
- **ビジネスロジック**: `app/application/annotation/` 新規作成
- **API**: `app/interfaces/api/annotation.py`, `annotation_auth.py` 新規作成
- **UI**: React + TypeScript + Tailwind CSS（別リポジトリまたは別ディレクトリ）

---

## 7. 次のステップ

1. **設計フェーズ開始**: `/kiro:spec-design sakura-vitality-annotation`
2. 設計ドキュメントで以下を詳細化:
   - DBスキーマ定義
   - API仕様（OpenAPI）
   - 画面遷移・UI設計
   - 認証フロー詳細

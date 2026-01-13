# Research & Design Decisions

## Summary
- **Feature**: `sakura-vitality-annotation`
- **Discovery Scope**: Extension（既存システムの拡張）
- **Key Findings**:
  - 既存の Admin 認証パターン（JWT + bcrypt）を流用可能
  - レイヤードアーキテクチャに沿った新規ドメイン `annotation` を追加
  - S3 画像取得は既存の ImageService を再利用

## Research Log

### 既存認証パターン調査
- **Context**: アノテーター認証の実装方式を決定するため
- **Sources Consulted**:
  - `app/interfaces/api/admin_auth.py` - 既存 Admin 認証実装
  - `app/domain/services/auth_service.py` - JWT トークン生成・検証
  - `app/domain/models/models.py` - Admin モデル定義
- **Findings**:
  - OAuth2PasswordBearer + JWT による認証が実装済み
  - bcrypt によるパスワードハッシュ化
  - トークン有効期限は 30 日間
  - `get_current_admin` 依存関数パターンで保護
- **Implications**: アノテーター認証も同パターンで実装。`Annotator` モデルと専用エンドポイント `/annotation_api/login` を新設

### データベース設計調査
- **Context**: アノテーション結果格納テーブルの設計
- **Sources Consulted**:
  - `app/domain/models/models.py` - 既存テーブル構造
  - `app/infrastructure/database/database.py` - DB 接続設定
- **Findings**:
  - SQLAlchemy 2.0 Mapped 型アノテーション使用
  - `entire_trees` テーブルに `tree_id` 外部キー
  - 要件指定: DB名 `hrkz_db`, ユーザー `hrkz_user`
- **Implications**: `vitality_annotations` テーブルと `annotators` テーブルを新設。`entire_tree_id` で関連付け

### S3 画像取得調査
- **Context**: 一覧・詳細画面での画像表示方法
- **Sources Consulted**:
  - `app/domain/services/image_service.py` - S3 画像操作
- **Findings**:
  - バケット: `hrkz-prd-s3-contents`
  - キーパス: `sakura_camera/media/trees/{image_obj_key}`
  - `get_image_url()` で公開 URL 生成
  - `get_presigned_url()` で署名付き URL 生成（1 時間有効）
- **Implications**: アノテーション画面では署名付き URL を使用して画像を表示

### 開花予想日データ調査
- **Context**: アノテーション画面での撮影情報表示
- **Sources Consulted**:
  - `app/domain/services/flowering_date_service.py` - 開花日取得サービス
  - `app/domain/models/flowering_date_spot.py` - 開花日スポットモデル
  - `app/interfaces/api/info.py` - `/sakura_camera/api/info/flowering_date` エンドポイント
- **Findings**:
  - CSV ファイル (`master/flowering_date.csv`) からマスターデータ読み込み
  - `FloweringDateService.find_nearest_spot(latitude, longitude)` で緯度経度から最寄りスポットを検索
  - 返却データ: `flowering_date`（開花予想日）, `full_bloom_date`（満開開始日）, `full_bloom_end_date`（満開終了日）
  - 既存 API: `GET /sakura_camera/api/info/flowering_date?latitude=...&longitude=...`
- **Implications**: Tree の緯度経度から `FloweringDateService.find_nearest_spot()` を呼び出して開花日を取得

### 都道府県・撮影場所データ調査
- **Context**: 一覧画面でのフィルタリングとアノテーション画面での情報表示
- **Sources Consulted**:
  - `app/domain/services/municipality_service.py` - 都道府県・自治体サービス
  - `app/domain/models/prefecture.py` - 都道府県モデル
  - `app/domain/constants/prefecture.py` - 都道府県コードマップ
  - `app/domain/models/models.py` - Tree モデル
- **Findings**:
  - `Tree.prefecture_code` に都道府県コード（JIS X 0401）が保存
  - `Tree.location` に撮影場所（自治体名）が保存
  - `MunicipalityService.get_prefecture_by_code(code)` で都道府県コードから都道府県名を取得
  - `MunicipalityService.prefectures` で全都道府県一覧を取得可能（フィルター用）
  - CSV ファイル (`master/pref_lat_lon.csv`) から都道府県マスターデータ読み込み
- **Implications**:
  - 都道府県名: `Tree.prefecture_code` → `MunicipalityService.get_prefecture_by_code(code).name`
  - 撮影場所: `Tree.location` から直接取得
  - フィルター用都道府県一覧: `MunicipalityService.prefectures` を API エンドポイントで提供

### フロントエンド技術調査
- **Context**: アノテーション Web UI の技術選定
- **Sources Consulted**:
  - `app/interfaces/templates/` - 既存 Jinja2 テンプレート
  - `app/interfaces/share/` - シェアページ実装
- **Findings**:
  - 既存システムは Jinja2 テンプレート + 静的 HTML
  - 管理画面は別フロントエンド（API 経由）の可能性
- **Implications**: アノテーションツールはシンプルな SPA として実装。バックエンド API + フロントエンド静的ファイル配信

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| 既存レイヤードアーキテクチャ拡張 | 新規 annotation ドメインを追加 | 一貫性維持、既存パターン踏襲 | なし | 採用 |
| 独立マイクロサービス | 別サービスとして分離 | 独立デプロイ可能 | 過剰設計、運用複雑化 | 不採用 |

## Design Decisions

### Decision: アノテーター認証の分離
- **Context**: Admin 認証と共用するか、別立てにするか
- **Alternatives Considered**:
  1. Admin テーブル共用 — ロールカラム追加
  2. Annotator テーブル新設 — 完全分離
- **Selected Approach**: Annotator テーブル新設
- **Rationale**: Admin と Annotator は異なる権限・用途。分離により影響範囲を限定
- **Trade-offs**: テーブル増加、認証エンドポイント追加
- **Follow-up**: 将来的に RBAC 導入時は統合検討

### Decision: アノテーション結果の上書き更新
- **Context**: 同一画像への再アノテーション時の挙動
- **Alternatives Considered**:
  1. 履歴保持（追記型）
  2. 最新値上書き
- **Selected Approach**: 最新値上書き（履歴不要の要件）
- **Rationale**: 要件に履歴参照の記載なし。シンプル実装優先
- **Trade-offs**: 変更履歴は追跡不可
- **Follow-up**: 必要に応じて audit_log 追加

### Decision: フロントエンド実装
- **Context**: アノテーション UI の実装方式
- **Alternatives Considered**:
  1. Jinja2 サーバーサイドレンダリング
  2. React SPA
  3. Vue.js SPA
  4. HTML + Vanilla JS
- **Selected Approach**: HTML + Vanilla JS（静的ファイル配信）
- **Rationale**: シンプルな UI、追加依存最小化、既存 API 構成との親和性
- **Trade-offs**: 複雑な状態管理には不向き
- **Follow-up**: 将来的に機能拡張時は SPA フレームワーク検討

## Risks & Mitigations
- **認証トークン漏洩リスク** — HTTPS 必須、短期トークン検討、Secure Cookie 使用
- **大量データ時のパフォーマンス** — ページネーション実装、インデックス最適化
- **S3 画像取得失敗** — エラーハンドリング、代替画像表示

## References
- [FastAPI Security - OAuth2](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) — JWT 認証パターン
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/) — Mapped 型アノテーション
- [boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html) — 署名付き URL 生成

# Research & Design Decisions

## Summary
- **Feature**: annotation-readiness-permission
- **Discovery Scope**: Extension（既存アノテーションシステムへの機能追加）
- **Key Findings**:
  - 既存 Annotator モデルに role カラムがなく、新規追加が必要
  - VitalityAnnotation テーブルに is_ready カラムを追加し、インデックスを設ける
  - 既存の JWT 認証パターン（AnnotationAuthService）を拡張してロール情報を含める

## Research Log

### 既存アノテーションシステムの構造分析
- **Context**: 本機能は既存のアノテーションツールへの拡張であり、既存パターンとの整合性が重要
- **Sources Consulted**:
  - `app/domain/models/annotation.py`
  - `app/interfaces/api/annotation.py`
  - `app/domain/services/annotation_auth_service.py`
  - `frontend/annotation-tool/src/hooks/useAuth.tsx`
- **Findings**:
  - `Annotator` モデル: id, username, hashed_password, last_login, created_at, updated_at のみ（role なし）
  - `VitalityAnnotation` モデル: is_ready カラムなし
  - 認証: JWT トークンに `is_annotator: true` のみ含み、ロール情報なし
  - フロントエンド: `useAuth` フックで annotator 情報を管理、role 情報なし
- **Implications**:
  - annotators テーブルに `role` VARCHAR(20) カラムを追加するマイグレーションが必要
  - vitality_annotations テーブルに `is_ready` BOOLEAN カラムを追加するマイグレーションが必要
  - JWT ペイロードに `role` フィールドを追加
  - フロントエンドの Annotator 型に `role` を追加

### 権限管理パターンの設計
- **Context**: admin/annotator の2種類のロールで機能を分離する必要がある
- **Sources Consulted**:
  - FastAPI 公式ドキュメント（Dependencies）
  - 既存の `get_current_annotator` 依存関数パターン
- **Findings**:
  - 既存の認証は `get_current_annotator` 依存関数で実現
  - ロールベース認可は追加の依存関数で実現可能
  - `Depends(require_admin)` パターンで管理者専用エンドポイントを保護
- **Implications**:
  - `require_admin` 依存関数を新規作成し、admin ロール以外は 403 を返す
  - 一覧・詳細取得は `get_current_annotator` を引き続き使用し、内部でロール判定
  - is_ready 変更エンドポイントには `require_admin` を適用

### is_ready フィルタリングの実装方針
- **Context**: annotator ロールは is_ready=TRUE のみ表示、admin ロールは全件表示
- **Sources Consulted**:
  - `app/application/annotation/annotation_list.py`
  - `app/application/annotation/annotation_detail.py`
- **Findings**:
  - 既存クエリは EntireTree → Tree → VitalityAnnotation の JOIN 構造
  - ステータスフィルターは `VitalityAnnotation.id.isnot(None)` / `is_(None)` で実現
  - is_ready フィルターも同様のパターンで追加可能
- **Implications**:
  - `AnnotationListFilter` に `is_ready_filter` パラメータを追加
  - annotator ロールの場合は自動的に `is_ready=TRUE` 条件を付与
  - admin ロールの場合は is_ready フィルターパラメータを任意で指定可能

### フロントエンド状態管理パターン
- **Context**: ロール情報に基づくUI制御が必要
- **Sources Consulted**:
  - `frontend/annotation-tool/src/hooks/useAuth.tsx`
  - `frontend/annotation-tool/src/types/api.ts`
  - `frontend/annotation-tool/src/pages/ListPage.tsx`
- **Findings**:
  - `AuthContext` で annotator 情報を保持
  - `getMe` API で認証済みユーザー情報を取得
  - ログイン後に annotator 情報を state に保存
- **Implications**:
  - `Annotator` 型に `role: 'admin' | 'annotator'` を追加
  - `useAuth` フックの `annotator` に role 情報が含まれる
  - コンポーネントで `annotator?.role === 'admin'` の条件分岐でUI制御

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| ロールカラム追加（単一テーブル） | annotators テーブルに role カラムを追加 | シンプル、既存構造との親和性高い | 複雑な権限階層には不向き | 採用：2ロールなら十分 |
| 別テーブル（roles + annotator_roles） | 権限を別テーブルで管理 | 拡張性高い、多対多対応 | 現時点では過剰設計 | 不採用：将来拡張時に検討 |
| is_ready を VitalityAnnotation に追加 | 既存テーブルにカラム追加 | 画像単位の管理が直接的 | NULL 許容の考慮が必要 | 採用：EntireTree との1:1関係で管理しやすい |

## Design Decisions

### Decision: ロール管理方式
- **Context**: admin と annotator の2種類の権限を区別する必要がある
- **Alternatives Considered**:
  1. annotators テーブルに role カラム追加 — シンプルな VARCHAR カラム
  2. 別テーブルでロール管理 — roles + annotator_roles の多対多
  3. JWT クレームのみでロール管理 — DBに保存しない
- **Selected Approach**: annotators テーブルに `role` VARCHAR(20) カラムを追加
- **Rationale**:
  - 2種類のロールのみで複雑な階層は不要
  - DB に永続化することで JWT 再発行なしにロール変更可能
  - 既存テーブル構造への最小限の変更
- **Trade-offs**:
  - 利点: シンプル、既存コードへの影響最小
  - 妥協: 将来的に複雑なロール階層が必要になった場合は再設計が必要
- **Follow-up**: デフォルト値を 'annotator' とし、既存データのマイグレーション時に設定

### Decision: is_ready フラグの配置
- **Context**: 画像ごとに「評価準備完了」状態を管理する必要がある
- **Alternatives Considered**:
  1. VitalityAnnotation テーブルに is_ready カラム追加
  2. EntireTree テーブルに is_ready カラム追加
  3. 別途 image_readiness テーブルを作成
- **Selected Approach**: VitalityAnnotation テーブルに `is_ready` BOOLEAN カラムを追加
- **Rationale**:
  - アノテーション情報と密接に関連するデータ
  - 既存の VitalityAnnotation との JOIN がそのまま活用可能
  - レコードがない場合は is_ready=FALSE として扱う設計
- **Trade-offs**:
  - 利点: 既存クエリ構造への影響が最小限
  - 妥協: VitalityAnnotation レコードがない場合は is_ready を設定できない → 別途レコード作成が必要
- **Follow-up**: is_ready のみを設定する場合、vitality_value=NULL の VitalityAnnotation レコードを作成するか、EntireTree に移動するか要検討

### Decision: is_ready の配置場所（修正）
- **Context**: 上記決定の再検討 — VitalityAnnotation に is_ready を追加すると、アノテーション未実施の画像に is_ready を設定できない問題がある
- **Alternatives Considered**:
  1. VitalityAnnotation に追加し、is_ready 設定時に空の VitalityAnnotation レコードを作成
  2. EntireTree に is_ready カラムを追加
- **Selected Approach**: VitalityAnnotation テーブルに `is_ready` BOOLEAN DEFAULT FALSE を追加し、is_ready 設定時にレコードを作成する
- **Rationale**:
  - 要件では「is_ready のみを変更」「アノテーションを保存」が別操作として定義
  - is_ready=TRUE を設定する際に vitality_value=NULL の VitalityAnnotation レコードを作成（UPSERT）
  - is_ready と vitality_value を同一レコードで管理することで、クエリがシンプルに保たれる
- **Trade-offs**:
  - 利点: 既存の JOIN 構造を維持、is_ready インデックスによる効率的なフィルタリング
  - 妥協: アノテーション未実施でも is_ready 設定のためにレコード作成が必要
- **Follow-up**: vitality_value を NULL 許容に変更するマイグレーションが必要

### Decision: API 認可パターン
- **Context**: 管理者専用エンドポイントへのアクセス制御が必要
- **Alternatives Considered**:
  1. 各エンドポイント内でロールチェック
  2. FastAPI Depends による依存関数でロールチェック
  3. ミドルウェアでルート単位のロールチェック
- **Selected Approach**: FastAPI Depends による `require_admin` 依存関数を作成
- **Rationale**:
  - 既存の `get_current_annotator` パターンとの一貫性
  - エンドポイント定義時に宣言的に権限を指定可能
  - テスト時のモック化が容易
- **Trade-offs**:
  - 利点: 再利用性、明示的な権限宣言
  - 妥協: エンドポイントごとに依存関数を指定する必要がある
- **Follow-up**: 将来的に複数ロールが必要になった場合、`require_role(roles: list[str])` パターンに拡張可能

### Decision: フロントエンドでのロール情報取得タイミング
- **Context**: UI 制御のためにフロントエンドでロール情報が必要
- **Alternatives Considered**:
  1. ログイン時のトークンレスポンスに role を含める
  2. `/me` エンドポイントのレスポンスに role を含める
  3. 両方に含める
- **Selected Approach**: `/me` エンドポイントのレスポンスに role を含める（要件 8.2）、ログインレスポンスはトークンのみ維持
- **Rationale**:
  - 既存の認証フローを変更しない
  - `getMe` で取得する annotator 情報に role を追加するだけでフロントエンドに反映
  - JWT ペイロードには role を含めてバックエンドでの認可に使用
- **Trade-offs**:
  - 利点: 既存ログインフローへの影響最小
  - 妥協: フロントエンドでロール取得に追加の API 呼び出しが必要（既存フローで実行済み）
- **Follow-up**: `AnnotatorResponse` スキーマに `role` フィールドを追加

## Risks & Mitigations
- **既存データのマイグレーション**: 既存 annotators レコードにデフォルト role を設定 → マイグレーションで `role = 'annotator'` をデフォルト設定
- **is_ready フィルターのパフォーマンス**: 大量データでのクエリ性能 → `is_ready` カラムにインデックスを作成
- **フロントエンドの権限チェック漏れ**: UI で非表示にしても API は呼び出せる → バックエンドで必ず認可チェック
- **vitality_value の NULL 許容化**: 既存データへの影響 → 既存レコードには影響なし（すでに値が設定済み）

## References
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) — 依存関数パターンの参考
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/) — Mapped 型アノテーション
- [Alembic Migration](https://alembic.sqlalchemy.org/en/latest/) — カラム追加マイグレーション

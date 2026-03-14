# Research & Design Decisions

## Summary
- **Feature**: annotation-version-diagnostics
- **Discovery Scope**: Extension（既存アノテーションシステムの拡張）
- **Key Findings**:
  - Treeモデルに`version`カラムは未存在 → Alembicマイグレーション必要
  - EntireTreeモデルに全診断値カラム（vitality系）と`bloom_30_date`/`bloom_50_date`は既存
  - デバッグ画像は`debug_image_obj_key`/`debug_image_obj2_key`としてEntireTreeに格納済み
  - 認証システムにadmin/annotatorロール区別は既存（`require_admin`依存性注入パターン）

## Research Log

### Treeモデルのversionカラム
- **Context**: 年度フィルタのためにTreeテーブルにversionカラムが必要
- **Findings**:
  - 現在のTreeモデル（`app/domain/models/models.py:40-103`）にversionカラムは存在しない
  - 既存レコードのデフォルト値は`2025_v01`、新規作成は`2026_v01`
  - Alembicマイグレーションで`version` VARCHAR(10) カラムをデフォルト`2025_v01`で追加
- **Implications**: マイグレーション1本で対応可能。既存レコードはデフォルト値で自動設定

### EntireTreeの診断値カラム
- **Context**: Admin向け診断値表示の対象カラムを確認
- **Findings**:
  - EntireTree（`models.py:105-175`）に以下が既存:
    - `vitality`, `vitality_noleaf`, `vitality_noleaf_weight`
    - `vitality_bloom`, `vitality_bloom_weight`
    - `vitality_bloom_30`, `vitality_bloom_30_weight`
    - `vitality_bloom_50`, `vitality_bloom_50_weight`
  - `bloom_30_date`, `bloom_50_date`も既存（`models.py:162-165`）
- **Implications**: 新規カラム追加不要。APIレスポンスにフィールドを追加するだけ

### デバッグ画像の格納パターン
- **Context**: セグメンテーション画像の提供方法を確認
- **Findings**:
  - EntireTreeに`debug_image_obj_key`と`debug_image_obj2_key`が存在（`models.py:138-139`）
  - 画像URLは`ImageService.get_image_url(object_key)`で生成（`image_service.py:104-105`）
  - 現在デバッグ画像を提供する専用エンドポイントは未実装
  - 要件の`entire_debug_noleaf_{uid}.jpg`/`entire_debug_bloom_{uid}.jpg`はS3キーのパターンに対応
- **Implications**: ImageServiceの既存パターンでURL生成可能。新規エンドポイントを追加

### 認証・権限パターン
- **Context**: Admin限定機能の実装パターン確認
- **Findings**:
  - `annotation_auth.py`に`require_admin()`依存性注入が既存（Lines 89-109）
  - `get_current_annotator()`でAnnotatorオブジェクト取得、roleフィールドで判定
  - 既存の`is_ready`機能がadmin限定パターンの参考例
  - アノテーション一覧APIに`vitality_value`フィルタは既存（ただし全ロール向け）
- **Implications**: admin限定フィルタは既存パターンを踏襲。レスポンスにrole情報を含めるか、フロントエンドで制御

### アノテーション一覧APIの現状
- **Context**: versionフィルタ追加のベースライン確認
- **Findings**:
  - `GET /trees`エンドポイント（`annotation.py:61-163`）
  - 既存フィルタ: status, prefecture_code, vitality_value, photo_date_from/to, is_ready, bloom_status
  - クエリは`EntireTree JOIN Tree`パターン（`annotation_list.py:109-120`）
  - ページネーション: offset/limit
- **Implications**: `version`クエリパラメータ（リスト型）を追加し、`Tree.version`でWHERE IN句を適用

### 開花段階日の算出
- **Context**: 3分咲き・5分咲き日表示の実装方式確認
- **Findings**:
  - `BloomStateService`（`bloom_state_service.py`）が都道府県オフセットCSVを使って算出
  - `bloom_30_date`/`bloom_50_date`はEntireTreeに既に格納済み
  - 詳細画面では`FloweringDateService`から最寄り地点の開花予想日を取得し表示
- **Implications**: EntireTreeの`bloom_30_date`/`bloom_50_date`をレスポンスに追加するだけ

## Design Decisions

### Decision: versionフィルタのAPI設計
- **Context**: フロントエンドのチェックボックスUIに対応するAPIパラメータ設計
- **Alternatives Considered**:
  1. 単一`version`パラメータ（整数値）
  2. `versions`パラメータ（カンマ区切り文字列リスト）
  3. `year_2025`/`year_2026`ブーリアンパラメータ
- **Selected Approach**: `versions`パラメータ（カンマ区切り、例: `versions=2025_v01,2026_v01`）
- **Rationale**: 既存の`bloom_status`パラメータがカンマ区切りリストで実装済み。同じパターンに合わせることで一貫性を保つ
- **Trade-offs**: 将来的な年度追加にも柔軟に対応可能

### Decision: Admin限定フィールドのレスポンス設計
- **Context**: 同一エンドポイントでroleによってレスポンスフィールドを変える方式
- **Alternatives Considered**:
  1. Admin専用エンドポイントを別途作成
  2. レスポンスにroleを含め、全フィールドを常に返却（フロントエンドで表示制御）
  3. roleに応じてレスポンスフィールドを動的に制御
- **Selected Approach**: Annotatorのroleをレスポンスのコンテキストとして利用し、Admin時のみ追加フィールドを返却
- **Rationale**: バックエンドでのアクセス制御が確実。診断値は内部データであり非Admin向けにリークすべきでない
- **Trade-offs**: レスポンススキーマがroleにより変動するが、Optional型で対応可能

### Decision: デバッグ画像表示の方式
- **Context**: セグメンテーション画像を別画面で表示する実装方式
- **Alternatives Considered**:
  1. 詳細APIレスポンスにURLを含め、フロントエンドで別画面遷移
  2. 専用のデバッグ画像取得エンドポイントを追加
- **Selected Approach**: 詳細APIレスポンスにAdmin向けデバッグ画像URLを含める
- **Rationale**: EntireTreeに`debug_image_obj_key`/`debug_image_obj2_key`が既存。ImageServiceでURL生成し、レスポンスに含めるだけで実現可能。別画面遷移はフロントエンド側の責務
- **Trade-offs**: 画像の存在確認はS3問い合わせが必要だが、URLの返却自体はDB値から生成するためオーバーヘッドは軽微

## Risks & Mitigations
- **Risk**: マイグレーション適用時の既存データへの影響 → デフォルト値`2025_v01`で安全に対応
- **Risk**: versionフィルタなし時のパフォーマンス → `version`カラムにインデックス追加
- **Risk**: デバッグ画像が存在しないケース → Optional型でnull返却、フロントエンドで「画像なし」表示

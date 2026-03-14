# ギャップ分析: annotation-version-diagnostics

## 分析サマリー

- **スコープ**: アノテーション機能への6つの拡張（年度バージョン、開花段階日、診断値表示、元気度フィルタ、デバッグ画像）
- **既存資産の充実度**: EntireTreeモデルに必要なフィールド（vitality_*、bloom_*_date）は全て既存。不足はTreeモデルの`version`カラムのみ
- **認証基盤**: admin/annotatorのロールベース認可が既に実装済み。Admin限定機能は既存パターンで実現可能
- **主なギャップ**: Treeへのversionカラム追加（DB migration）、APIレスポンスへの診断値・デバッグ画像情報の追加、フィルタパラメータの拡張
- **推奨アプローチ**: 既存コンポーネントの拡張（Option A）が最適。新規ファイル作成は最小限

---

## 要件-資産マッピング

### Requirement 1: 年度バージョンカラム追加

| 技術要素 | 既存資産 | ギャップ |
|---------|---------|---------|
| Treeモデル | `app/domain/models/models.py` (Tree) | **Missing**: `version` カラムが未定義 |
| DBマイグレーション | `alembic/versions/` にパターン確立済み | **Missing**: version追加のマイグレーションファイル |
| 木登録処理 | `app/infrastructure/repositories/tree_repository.py` の `create_tree()` | **Missing**: 新規作成時に `version=202601` を設定するロジック |
| 既存データ | 全既存レコード | **Missing**: デフォルト値 `202501` の適用（マイグレーションで対応） |

### Requirement 2: 年度フィルタUI

| 技術要素 | 既存資産 | ギャップ |
|---------|---------|---------|
| リストAPI | `app/interfaces/api/annotation.py` GET `/trees` | **Missing**: `version` クエリパラメータ |
| リストクエリ | `app/application/annotation/annotation_list.py` | **Missing**: version条件のWHERE句 |
| スキーマ | `app/interfaces/schemas/annotation.py` | **Missing**: versionフィルタのリクエスト/レスポンスフィールド |
| CSV出力 | `app/application/annotation/export_csv.py` | **Missing**: versionフィルタの適用 |

**備考**: 既存のフィルタパターン（prefecture_code、bloom_status等）がそのまま踏襲可能。

### Requirement 3: 開花段階日表示

| 技術要素 | 既存資産 | ギャップ |
|---------|---------|---------|
| EntireTreeフィールド | `bloom_30_date`, `bloom_50_date` 定義済み | なし |
| 詳細API | `annotation_detail.py` | **Missing**: bloom_30_date, bloom_50_dateのレスポンスへの追加 |
| レスポンススキーマ | `AnnotationDetailResponse` | **Missing**: bloom_30_date, bloom_50_dateフィールド |
| FloweringDateService | 最寄りスポットの開花日計算済み | なし（既存ロジック利用可能） |

**備考**: `annotation_detail.py`では既に`flowering_date`と`full_bloom_start_date`を返却しており、同じパターンで`bloom_30_date`と`bloom_50_date`を追加するだけ。

### Requirement 4: 診断値表示（Admin限定）

| 技術要素 | 既存資産 | ギャップ |
|---------|---------|---------|
| EntireTreeフィールド | vitality, vitality_noleaf, vitality_noleaf_weight, vitality_bloom, vitality_bloom_weight, vitality_bloom_30, vitality_bloom_30_weight, vitality_bloom_50, vitality_bloom_50_weight 全て定義済み | なし |
| 詳細API | `get_tree_detail()` で `get_current_annotator` 依存 | **Missing**: Admin判定によるレスポンス切替 |
| レスポンススキーマ | `AnnotationDetailResponse` | **Missing**: 診断値フィールド群（Admin限定） |
| Admin認可 | `require_admin` 依存関数が既存 | なし |

**備考**: 詳細APIでは現在 `get_current_annotator` のみ使用。Admin判定はannotatorのroleフィールドで可能（`annotator.role == "admin"`）。`require_admin`を使うとAdmin以外がアクセス不可になるため、条件付きレスポンス切替が適切。

### Requirement 5: 元気度フィルタ（Admin限定）

| 技術要素 | 既存資産 | ギャップ |
|---------|---------|---------|
| リストAPI | GET `/trees` に `vitality_value` パラメータ既存 | 要確認: 現在の挙動とAdmin制限 |
| リストクエリ | `annotation_list.py` で vitality_value フィルタ既存 | **Missing**: Admin限定の制御（現在は全ユーザーが使用可能） |
| CSV出力 | `export_csv.py` | 同様にAdmin限定制御が必要 |

**備考**: **重要発見** — `vitality_value`フィルタは既に実装済み。ただし現在は全ユーザーが使用可能。要件ではAdmin限定とされているため、annotatorロールの場合にこのパラメータを無視する制御の追加が必要。

### Requirement 6: デバッグ画像表示（Admin限定）

| 技術要素 | 既存資産 | ギャップ |
|---------|---------|---------|
| S3キー | `debug_image_obj_key`, `debug_image_obj2_key` がEntireTreeに定義済み | なし |
| 画像URL生成 | S3署名付きURL生成パターン既存（image_obj_keyで利用） | 流用可能 |
| 詳細API | `get_tree_detail()` | **Missing**: デバッグ画像URLのレスポンス追加（Admin限定） |
| 別画面表示 | — | **Missing**: デバッグ画像表示用エンドポイントまたはURL |
| レスポンススキーマ | `AnnotationDetailResponse` | **Missing**: debug_image_urlsフィールド |

**備考**: 「別画面で表示」はフロントエンド側の責務だが、APIとしてはデバッグ画像のURLを返却する必要がある。S3オブジェクトキーから署名付きURLを生成するパターンは既存。

---

## 実装アプローチの選択肢

### Option A: 既存コンポーネント拡張（推奨）

**適用理由**: 全要件が既存のアノテーション機能の拡張であり、新たな責務の追加ではない

**変更対象ファイル**:

| ファイル | 変更内容 |
|---------|---------|
| `app/domain/models/models.py` | Tree に `version` カラム追加 |
| `alembic/versions/` | 新規マイグレーション（version カラム追加） |
| `app/interfaces/api/annotation.py` | version フィルタパラメータ追加、レスポンス拡張 |
| `app/interfaces/schemas/annotation.py` | version、診断値、bloom_30/50_date、debug_image_urls フィールド追加 |
| `app/application/annotation/annotation_list.py` | version フィルタ条件追加、vitality_value の Admin 限定化 |
| `app/application/annotation/annotation_detail.py` | 診断値・デバッグ画像URL・bloom日の返却追加 |
| `app/application/annotation/export_csv.py` | version フィルタ対応 |
| `app/infrastructure/repositories/tree_repository.py` | create_tree で version=202601 設定 |

**トレードオフ**:
- ✅ 既存パターンの踏襲で一貫性維持
- ✅ 新規ファイル最小限（マイグレーションのみ）
- ✅ 既存テストの拡張で対応可能
- ❌ annotation_list.py（418行）、annotation_detail.py（302行）がさらに肥大化する可能性

### Option B: 新規コンポーネント分離

**適用場面**: 診断値・デバッグ機能を独立エンドポイントとして分離

**新規ファイル**:
- `app/interfaces/api/annotation_diagnostics.py` — 診断値・デバッグ画像用エンドポイント
- `app/application/annotation/diagnostics.py` — 診断関連ロジック

**トレードオフ**:
- ✅ 既存コードへの影響最小
- ✅ Admin機能の明確な分離
- ❌ 詳細画面のデータを2回のAPIコールで取得する必要
- ❌ 過剰設計の可能性（機能規模に対してファイル数が多い）

### Option C: ハイブリッド

**戦略**: version フィルタ・bloom日表示は既存拡張、デバッグ画像表示は新規エンドポイント

**トレードオフ**:
- ✅ デバッグ画像の「別画面表示」要件に自然に対応
- ✅ 既存エンドポイントの変更を抑制
- ❌ 判断基準が曖昧で一貫性に欠ける可能性

---

## 実装複雑度とリスク

### 工数見積: **S（1〜3日）**

**根拠**:
- 全要件が既存パターンの拡張
- 新規テクノロジー・外部連携なし
- モデルフィールドは全て既存（versionカラム追加のみ）
- 認可パターン（admin/annotator）確立済み

### リスク: **Low**

**根拠**:
- 使い慣れた技術スタック内での変更
- 既存のフィルタ・レスポンスパターンの踏襲
- DBマイグレーションは単純なカラム追加（デフォルト値付き）
- 影響範囲がAnnotation APIに限定

---

## 設計フェーズへの推奨事項

### 推奨アプローチ: Option A（既存拡張）+ デバッグ画像エンドポイントのみOption C的に分離

1. **version フィルタ**: 既存リストAPIにクエリパラメータ追加。複数選択対応（bloom_statusの複数値フィルタと同パターン）
2. **bloom日表示**: 既存の詳細レスポンスにフィールド追加のみ
3. **診断値表示**: 詳細レスポンスにAdmin限定フィールドを追加。annotatorのroleで出し分け
4. **vitality フィルタ**: 既存実装のAdmin限定化
5. **デバッグ画像**: S3署名付きURLを詳細レスポンスに含めるか、専用エンドポイントにするか設計フェーズで決定

### リサーチ項目（設計フェーズで確認）

- **Research Needed**: デバッグ画像の命名規則（`entire_debug_noleaf_{uid}.jpg` / `entire_debug_bloom_{uid}.jpg`）と、EntireTreeの`debug_image_obj_key` / `debug_image_obj2_key`の対応関係
- **Research Needed**: デバッグ画像の「別画面」表示がフロントエンド実装のみで済むか、API側で専用エンドポイントが必要か
- **Research Needed**: version値の将来的な拡張性（202701等の追加可能性）— 現時点ではチェックボックスUIだが、将来的にドロップダウン等への変更が必要になる可能性

---

_generated_at: 2026-03-14_

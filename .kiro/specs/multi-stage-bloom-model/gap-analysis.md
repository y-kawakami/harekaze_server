# ギャップ分析: multi-stage-bloom-model

## 分析サマリー

- **スコープ**: `POST /sakura_camera/api/tree/entire` の樹勢判定ロジックを2モデル→4モデル方式へ拡張
- **主な課題**: 開花段階判定ロジックの新規実装、AIService への2エンドポイント追加、EntireTree モデルへのフィールド追加、DB マイグレーション
- **既存資産の活用度**: 高い。`BloomStateService.get_prefecture_offsets()` と `FloweringDateService.find_nearest_spot()` は既に存在し、そのまま利用可能
- **推奨アプローチ**: ハイブリッド方式（既存 `create_tree.py` の拡張 + 新規開花段階判定サービス作成）
- **工数**: M（3〜7日）、リスク: 中

---

## 1. 現状調査（Current State Investigation）

### 1.1 関連ファイル・モジュール一覧

| コンポーネント | ファイルパス | 役割 |
|---|---|---|
| エンドポイント | `app/interfaces/api/tree.py:73-136` | HTTP ルート定義 |
| ユースケース | `app/application/tree/create_tree.py:41-353` | 樹勢判定オーケストレーション |
| AIサービス | `app/domain/services/ai_service.py` | REST API 呼び出し（2モデル） |
| Lambda サービス | `app/domain/services/lambda_service.py` | Lambda 経由 AI 呼び出し（代替） |
| 開花日サービス | `app/domain/services/flowering_date_service.py` | 最寄りスポット検索 |
| 開花状態サービス | `app/domain/services/bloom_state_service.py` | 都道府県オフセット・開花状態計算 |
| 重み計算 | `app/domain/models/flowering_date_spot.py:39-96` | `estimate_vitality()` 2モデル重み算出 |
| データモデル | `app/domain/models/models.py:104-153` | EntireTree モデル定義 |
| リポジトリ | `app/infrastructure/repositories/tree_repository.py:45-130` | DB 保存 |

### 1.2 現在のフロー（`create_tree.py`）

```
1. 画像アップロード → S3
2. 2つの AI モデルを並列呼び出し:
   - analyze_tree_vitality_bloom()    → /analyze/image/vitality/bloom
   - analyze_tree_vitality_noleaf()   → /analyze/image/vitality/noleaf
3. FloweringDateService.find_nearest_spot(lat, lon) で最寄りスポット取得
4. spot.estimate_vitality(target_datetime) → (noleaf_weight, bloom_weight)
5. ブレンド: vitality_real = noleaf_result * noleaf_weight + bloom_result * bloom_weight
6. DB 保存（EntireTree）
```

### 1.3 既存の `estimate_vitality()` ロジック

`FloweringDateSpot.estimate_vitality()` は日付ベースの2モデル重み計算:
- 開花前: `(1.0, 0.0)` — noleaf のみ
- 開花〜満開: 線形補間 `(1.0→0.0, 0.0→1.0)`
- 満開中: `(0.0, 1.0)` — bloom のみ
- 散り〜葉桜: 線形補間 `(0.5→1.0, 0.5→0.0)`
- 葉桜以降: `(1.0, 0.0)` — noleaf のみ

### 1.4 既存の `BloomStateService` の関連機能

- `get_prefecture_offsets(prefecture_code)` → `PrefectureOffsets` dataclass:
  - `flowering_to_3bu`: 開花→3分咲きオフセット（日数）
  - `flowering_to_5bu`: 開花→5分咲きオフセット（日数）
  - `end_to_hanawakaba`: 満開終了→花若葉オフセット
  - `end_to_hanami`: 満開終了→葉桜オフセット
- `calculate_bloom_status()`: 8段階の開花ステータス判定（bloom-status-filter 用）

### 1.5 AIService の現在のエンドポイント

```python
api_path_vitality_bloom = "/analyze/image/vitality/bloom"
api_path_vitality_noleaf = "/analyze/image/vitality/noleaf"
# bloom_30_percent, bloom_50_percent は未実装
```

### 1.6 EntireTree モデルの現在のフィールド

```
vitality, vitality_real                        # 最終ブレンド結果
vitality_bloom, vitality_bloom_real, vitality_bloom_weight    # 満開モデル結果
vitality_noleaf, vitality_noleaf_real, vitality_noleaf_weight  # 枝のみモデル結果
bloom_status                                   # 開花状態（文字列）
```

**不足フィールド**: `vitality_bloom_30`, `vitality_bloom_30_real`, `vitality_bloom_30_weight`, `vitality_bloom_50`, `vitality_bloom_50_real`, `vitality_bloom_50_weight`

---

## 2. 要件実現可能性分析

### 2.1 要件ごとの技術ニーズとギャップ

| 要件 | 技術ニーズ | 既存資産 | ギャップ |
|---|---|---|---|
| Req1: 開花段階判定 | 4段階判定ロジック | `FloweringDateService`, `BloomStateService` あり | **新規**: 補正済みオフセットを使った4段階判定ロジック |
| Req2: オフセット補正 | 比率算出・補正計算 | `get_prefecture_offsets()` あり | **新規**: 「開花〜満開実日数」÷「基準期間」の比率計算 |
| Req3: マルチステージ AI | 4つの AI エンドポイント | bloom, noleaf あり | **Missing**: `bloom_30_percent`, `bloom_50_percent` メソッド |
| Req4: 満開後ブレンド | 2モデルブレンド | 類似ロジック（`estimate_vitality`）あり | **拡張**: 満開後1週間限定のブレンド（既存と異なる条件） |
| Req5: 判定結果保存 | DB フィールド追加 | 2モデル分は既存 | **Missing**: 3分咲き・5分咲きモデルの保存フィールド |
| Req6: フォールバック | エラーハンドリング | 基本的なリトライあり | **拡張**: 新モデル失敗時のフォールバックチェーン |

### 2.2 複雑度シグナル

- **アルゴリズムロジック**: オフセット補正計算、4段階判定は中程度の複雑さ
- **外部統合**: 新規 AI エンドポイント2本の追加（既存パターンに沿って追加可能）
- **DB マイグレーション**: フィールド追加（nullable カラム追加なので低リスク）
- **フォールバック**: 複数レベルのフォールバック設計が必要

### 2.3 Research Needed

- [ ] オフセット補正の「基準オフセットが前提とする開花〜満開期間」の具体的な基準値の確認（CSV データから推定可能か、固定値か）
- [ ] `LambdaService` にも同様の `bloom_30_percent`、`bloom_50_percent` メソッド追加が必要かの確認
- [ ] 満開終了予想日（`full_bloom_end_date`）の定義確認（`FloweringDateSpot` に既に `full_bloom_end_date` フィールドが存在するか）

---

## 3. 実装アプローチ選択肢

### Option A: 既存コンポーネント拡張

**概要**: `create_tree.py` と関連サービスを直接拡張

**変更対象**:
- `app/domain/services/ai_service.py`: `analyze_tree_vitality_bloom_30_percent()`, `analyze_tree_vitality_bloom_50_percent()` 追加
- `app/domain/services/lambda_service.py`: 同上（Lambda 版）
- `app/application/tree/create_tree.py`: 4段階判定 + ブレンドロジックをインライン実装
- `app/domain/models/models.py`: EntireTree にフィールド追加
- `app/infrastructure/repositories/tree_repository.py`: 新フィールド保存
- `app/domain/models/flowering_date_spot.py`: `estimate_vitality()` を4モデル対応に拡張 or 新メソッド追加

**トレードオフ**:
- ✅ ファイル数増加なし、既存パターンとの一貫性が高い
- ✅ 変更箇所が明確
- ❌ `create_tree.py` が既に 353 行あり、ロジック追加でさらに肥大化
- ❌ 開花段階判定ロジックがユースケース層に埋もれる

### Option B: 新規コンポーネント作成

**概要**: 開花段階判定を専用ドメインサービスとして新規作成

**新規ファイル**:
- `app/domain/services/bloom_stage_judgment_service.py`: 開花段階判定 + オフセット補正ロジック

**変更対象**:
- `app/domain/services/ai_service.py`: 新エンドポイント追加
- `app/domain/services/lambda_service.py`: 同上
- `app/application/tree/create_tree.py`: 新サービスを呼び出すように変更
- `app/domain/models/models.py`: フィールド追加
- `app/infrastructure/repositories/tree_repository.py`: フィールド保存

**トレードオフ**:
- ✅ 開花段階判定ロジックが独立しテスト容易
- ✅ `create_tree.py` の肥大化を防ぐ
- ✅ 既存の `BloomStateService.calculate_bloom_status()` との責務分離が明確
- ❌ 新規ファイル追加（ただし1ファイル）
- ❌ `BloomStateService` と一部ロジックが重複する可能性

### Option C: ハイブリッドアプローチ（推奨）

**概要**: 開花段階判定ロジックを新規サービスとして切り出し、`create_tree.py` のオーケストレーションフローを拡張

**戦略**:
1. **新規**: `bloom_stage_judgment_service.py` — 4段階判定 + オフセット補正（`BloomStateService` と `FloweringDateService` を利用）
2. **拡張**: `ai_service.py` / `lambda_service.py` — 2つの新エンドポイントメソッド追加
3. **拡張**: `create_tree.py` — 新フローに書き換え（新サービスを呼び出し、判定結果に基づきモデル選択）
4. **拡張**: `models.py`, `tree_repository.py` — フィールド追加
5. **維持**: `estimate_vitality()` — フォールバック用に既存ロジックをそのまま残す

**フロー変更イメージ**:
```
[現在]
  2モデル並列呼び出し → estimate_vitality() → ブレンド

[新規]
  1. BloomStageJudgmentService で開花段階を判定
     → BloomStateService + FloweringDateService を活用
  2. 判定結果に基づき適切なモデルを呼び出し（1モデル or 2モデルブレンド）
  3. DB に結果・モデル種類・重みを保存

  ※ 判定失敗時は estimate_vitality() にフォールバック
```

**トレードオフ**:
- ✅ 開花段階判定ロジックが独立（テスト容易）
- ✅ 既存フォールバックパスを維持
- ✅ `create_tree.py` のオーケストレーション責務が明確
- ✅ `BloomStateService` を活用しつつ責務を分離
- ❌ 新規ファイル1つ追加
- ❌ 段階判定 → モデル選択 → 呼び出しの3ステップで、既存の並列呼び出しパターンが変わる

---

## 4. 実装複雑度 & リスク

### 工数: M（3〜7日）

**根拠**:
- 新パターンの導入は限定的（既存アーキテクチャに沿った追加）
- AI エンドポイント追加は既存メソッドのコピー＆改変
- DB マイグレーションは nullable カラム追加で低リスク
- 主な工数はオフセット補正ロジックの実装とテスト

### リスク: 中

**根拠**:
- オフセット補正の「基準期間」の定義が不明確（要確認）
- 新 AI エンドポイント（bloom_30_percent, bloom_50_percent）の API 仕様確認が必要
- `create_tree.py` の既存フロー変更による回帰リスク
- `LambdaService` への変更要否の確認が必要

---

## 5. 要件 → 既存資産マッピング

| 要件 | 既存資産 | ギャップタグ |
|---|---|---|
| Req1-AC1: 最寄りスポット取得 | `FloweringDateService.find_nearest_spot()` | ✅ 既存 |
| Req1-AC2: 4段階判定 | — | **Missing**: 新規判定ロジック |
| Req1-AC3: オフセット補正 | `BloomStateService.get_prefecture_offsets()` | **Missing**: 比率補正計算 |
| Req1-AC4〜9: 段階別条件分岐 | — | **Missing**: 新規ロジック |
| Req2-AC1: オフセット取得 | `PrefectureOffsets` dataclass | ✅ 既存 |
| Req2-AC2: 比率算出 | — | **Missing**: 基準期間の定義・計算 |
| Req2-AC3: 補正適用 | — | **Missing**: 新規計算 |
| Req2-AC4: フォールバック | `estimate_vitality()` | ✅ 既存（フォールバック先） |
| Req3-AC1: noleaf 呼び出し | `ai_service.analyze_tree_vitality_noleaf()` | ✅ 既存 |
| Req3-AC2: bloom_30 呼び出し | — | **Missing**: 新規メソッド |
| Req3-AC3: bloom_50 呼び出し | — | **Missing**: 新規メソッド |
| Req3-AC4: bloom 呼び出し | `ai_service.analyze_tree_vitality_bloom()` | ✅ 既存 |
| Req3-AC5: 結果返却 | `TreeVitalityBloomResult` 等 | ✅ 既存パターン |
| Req4-AC1〜4: ブレンドロジック | 類似ロジック（`create_tree.py:250-254`） | **拡張**: 条件変更 |
| Req5-AC1〜4: 結果保存 | `tree_repository.create_tree()` | **Missing**: 3分咲き・5分咲きフィールド |
| Req6-AC1〜2: フォールバック | `estimate_vitality()` | ✅ 既存 |
| Req6-AC3: モデル失敗時 | — | **Missing**: カスケードフォールバック |
| Req6-AC4: タイムアウト | `_call_api_with_bytes()` リトライ | ✅ 既存 |

---

## 6. 設計フェーズへの推奨事項

### 推奨アプローチ
**Option C（ハイブリッド）** を推奨。開花段階判定ロジックの独立性を保ちつつ、既存パターンへの影響を最小限にする。

### 設計フェーズでの検討事項

1. **基準期間の定義**: オフセット補正の「基準オフセットが前提とする開花〜満開期間」を CSV データから推定するか、固定値として定義するか
2. **LambdaService 対応**: AIService と同様に LambdaService にも新メソッドを追加するか
3. **並列 vs 逐次呼び出し**: 現在は2モデル並列だが、新方式では判定後に1モデルのみ呼ぶケースが増える。パフォーマンス影響を検討
4. **DB マイグレーション戦略**: 既存データの null 扱い、Alembic マイグレーションスクリプト
5. **`bloom_status` フィールドの更新**: 新しい4段階判定結果を既存の `bloom_status` フィールドに反映するか、別フィールドにするか
6. **テスト戦略**: 開花段階判定ロジックの単体テスト（日付境界テストケース）、create_tree のインテグレーションテスト

---

_generated_at: 2026-02-25_

# リサーチ & 設計判断ログ

## サマリー
- **機能名**: `multi-stage-bloom-model`
- **ディスカバリースコープ**: Extension（既存システムの拡張）
- **主要な発見事項**:
  - 現行の `create_tree` は常に noleaf / bloom の2モデルを並列呼び出しし、`FloweringDateSpot.estimate_vitality()` で線形ブレンドしている
  - `BloomStateService` は都道府県別 CSV から `flowering_to_3bu`・`flowering_to_5bu` オフセットを既に保持しているが、基準期間（開花→8分咲き日数）は未保存
  - AI API は REST ベースであり、新エンドポイント `/bloom_30_percent`・`/bloom_50_percent` も同一インターフェースで呼び出し可能

## リサーチログ

### 既存ブレンドロジックの構造
- **コンテキスト**: 現行の2モデルブレンドがどのように動作しているかを把握する
- **調査元**: `app/domain/models/flowering_date_spot.py` — `estimate_vitality()`
- **発見事項**:
  - `estimate_vitality` は `FloweringDateSpot` のメソッドで、`flowering_date`・`full_bloom_date`・`full_bloom_end_date` のみを使用
  - 都道府県別オフセットは使用していない（直接日付比較のみ）
  - 満開後のフォールオフは固定5日間（`full_bloom_end_date + timedelta(days=5)`）
  - 返却値は `(noleaf_weight, bloom_weight)` のタプル
- **含意**: 新しい多段階ロジックは `estimate_vitality` を置き換える形になるが、フォールバック用に旧ロジックは保持する必要がある

### CSV データ構造と基準期間
- **コンテキスト**: オフセット補正に必要な「基準期間」の算出方法を特定する
- **調査元**: `master/260121_bloom_state.csv`、`app/domain/services/bloom_state_service.py`
- **発見事項**:
  - CSV カラム: `[0]都道府県コード, [1]ステータス, [2]開花, [3]3分咲き, [4]5分咲き, [5]8分咲き（満開）, [6]散り始め, [7]花＋若葉, [8]葉のみ`
  - `PrefectureOffsets` には `flowering_to_3bu`・`flowering_to_5bu`・`end_to_hanawakaba`・`end_to_hanomi` の4フィールドのみ
  - 基準期間 = `(row[5]の8分咲き日 - row[2]の開花日).days` として算出可能（例: 北海道=5日、宮城=6日）
  - 現在の `_load_bloom_state_csv` は row[5] をパースしていない
- **含意**: `PrefectureOffsets` に `flowering_to_full_bloom: int` フィールドを追加し、CSV パース時に row[5] から算出する必要がある

### オフセット補正計算の設計
- **コンテキスト**: 要件2.2-2.3 のオフセット補正比率の具体的な計算方法
- **調査元**: requirements.md 要件2
- **発見事項**:
  - 補正比率 = `(spot.full_bloom_date - spot.flowering_date).days / offsets.flowering_to_full_bloom`
  - 補正済み3分咲きオフセット = `offsets.flowering_to_3bu * ratio`
  - 補正済み5分咲きオフセット = `offsets.flowering_to_5bu * ratio`
  - 例: 北海道(基準5日)のスポットで実際の開花→満開が7日の場合、ratio=1.4、3分咲きオフセット1日→1.4日
- **含意**: `ratio` は浮動小数点で算出し、オフセットも float で保持する。日付計算時に `timedelta(days=float)` で適用

### AI API エンドポイント互換性
- **コンテキスト**: 新規モデルエンドポイントが既存パターンに適合するか確認
- **調査元**: `app/domain/services/ai_service.py`
- **発見事項**:
  - 全モデルは同一の REST インターフェース（multipart/form-data で image + output_bucket + output_key）
  - レスポンス構造も統一: `{status, data: {vitality, vitality_real, vitality_probs, debug_image_key}}`
  - 新エンドポイント `/analyze/image/vitality/bloom_30_percent` と `/analyze/image/vitality/bloom_50_percent` も同一契約
- **含意**: `AIService` に新メソッドを追加するだけで対応可能。既存の `_call_api_with_bytes` をそのまま利用できる

### DB スキーマ拡張の影響
- **コンテキスト**: `EntireTree` テーブルへのカラム追加の影響範囲
- **調査元**: `app/domain/models/models.py`、`app/infrastructure/repositories/tree_repository.py`
- **発見事項**:
  - 現行: `vitality_noleaf*`（3カラム）+ `vitality_bloom*`（3カラム）= 6カラム
  - 追加: `vitality_bloom_30*`（3カラム）+ `vitality_bloom_50*`（3カラム）= 6カラム
  - `TreeRepository.create_tree()` に新パラメータを追加する必要がある
  - 既存データには影響なし（新カラムは全て `Optional`/`NULL` 許可）
- **含意**: Alembic マイグレーションで `ALTER TABLE ADD COLUMN` のみ。既存レコードは `NULL` のまま

### 条件付きモデル呼び出しによるパフォーマンス最適化
- **コンテキスト**: 必要なモデルのみ呼び出すことでレイテンシを削減できるか
- **調査元**: `app/application/tree/create_tree.py`
- **発見事項**:
  - 現行は常に2モデル並列呼び出し（`asyncio.gather`）
  - 新設計では開花段階により1モデルまたは2モデル呼び出し
  - 単一モデルの場合、AI API 呼び出しが1回で済むためレイテンシ約50%削減
  - ブレンド期間でも2モデル並列で現行と同等
- **含意**: 条件分岐で呼び出すモデルを動的に決定し、`asyncio.gather` で並列実行する設計が最適

## アーキテクチャパターン評価

| オプション | 説明 | 強み | リスク/制限 | 備考 |
|-----------|------|------|------------|------|
| 新サービス追加 | `MultiStageBloomService` を新規ドメインサービスとして作成 | 既存コードへの影響最小、単一責務、テスト容易 | サービス数が増加 | 採用 |
| BloomStateService 拡張 | 既存 `calculate_bloom_status()` を拡張 | コード集約 | 責務が混在（状態判定 + 重み算出）、テスト複雑化 | 不採用 |
| FloweringDateSpot 拡張 | `estimate_vitality()` を多段階対応に改修 | 変更箇所が少ない | フォールバックとの切り替えが複雑、dataclass の肥大化 | 不採用 |

## 設計判断

### 判断: 新規ドメインサービス `MultiStageBloomService` の導入
- **コンテキスト**: 4段階モデル選択ロジックをどこに配置するか
- **候補**:
  1. `BloomStateService.calculate_bloom_status()` を拡張 — 既存の8段階判定と責務が異なる
  2. `FloweringDateSpot.estimate_vitality()` を改修 — フォールバック保持が困難
  3. 新規 `MultiStageBloomService` — 単一責務で独立
- **選択**: オプション3 — `MultiStageBloomService`
- **理由**: 開花段階判定 + オフセット補正 + モデル選択 + ブレンド重み算出を一つのサービスに集約しつつ、既存コードを変更しない。フォールバック時は旧 `estimate_vitality` をそのまま使える
- **トレードオフ**: サービス数が1つ増えるが、テスト容易性と保守性のメリットが上回る
- **フォローアップ**: テストで各開花段階の境界値を網羅的に検証

### 判断: 条件付きモデル呼び出し
- **コンテキスト**: 全4モデルを常に呼び出すか、段階に応じて必要なモデルのみ呼び出すか
- **候補**:
  1. 常に全4モデル呼び出し — 実装シンプルだがレイテンシ・コスト増
  2. 段階に応じて1-2モデルのみ呼び出し — レイテンシ削減、コスト削減
- **選択**: オプション2 — 条件付き呼び出し
- **理由**: 単一モデル段階（3分咲き、5分咲き、満開、枝のみ）が多数を占めるため、不要な API 呼び出しを削減する効果が大きい
- **トレードオフ**: 条件分岐が増えるが、開花段階判定結果を元にした明確なディスパッチで管理可能

## リスク & 緩和策
- **リスク1**: 新 AI モデルエンドポイントの応答遅延 — 既存リトライロジック適用 + タイムアウト設定で緩和
- **リスク2**: CSV オフセット補正で極端な比率（0 除算含む） — `flowering_to_full_bloom == 0` 時はフォールバックに切り替え
- **リスク3**: DB マイグレーション時の既存データ整合性 — 全新カラムは `NULL` 許可のため影響なし

## 参考資料
- `master/260121_bloom_state.csv` — 都道府県別開花データ
- `master/flowering_date.csv` — 開花予想スポットデータ
- `app/domain/models/flowering_date_spot.py` — 現行ブレンドロジック
- `app/domain/services/bloom_state_service.py` — 都道府県別オフセット管理

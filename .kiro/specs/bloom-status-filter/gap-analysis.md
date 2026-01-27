# Gap Analysis: 開花状態フィルター機能

## 分析サマリー

本分析では、開花状態（bloom status）フィルター機能の実装に必要なコードベースの現状と要件のギャップを調査しました。

**主な発見:**
- 開花状態計算ロジックは既に`annotation_detail.py`の`_calculate_bloom_status()`に部分実装あり
- ただし現在の実装は簡易版で、要件で定義された8ステータス・都道府県別オフセットに対応していない
- `260121_bloom_state.csv`が新たに追加されており、この都道府県別データをパースする機能が必要
- EntireTreeモデルにbloom_statusカラムの追加とマイグレーションが必要
- フロントエンド・バックエンド両方でフィルター/統計機能の拡張が必要

**実装推奨アプローチ:** ハイブリッドアプローチ（オプションC）
- 既存のFloweringDateServiceを拡張して新CSVを読み込む
- 新規のBloomStatusServiceを作成して8ステータス判定ロジックを実装
- 既存のアノテーション一覧/詳細APIを拡張してフィルター・統計機能を追加

---

## 1. 現状調査

### 1.1 ドメイン関連のアセット

#### 主要ファイル構成
| 層 | ファイル | 責務 |
|---|---|---|
| Domain | `app/domain/models/models.py` | EntireTreeモデル定義 |
| Domain | `app/domain/models/annotation.py` | VitalityAnnotationモデル定義 |
| Domain | `app/domain/services/flowering_date_service.py` | 開花日取得サービス |
| Application | `app/application/annotation/annotation_list.py` | 一覧取得ユースケース |
| Application | `app/application/annotation/annotation_detail.py` | 詳細取得ユースケース（bloom_status計算あり） |
| Interface | `app/interfaces/api/annotation.py` | アノテーションAPIエンドポイント |
| Interface | `app/interfaces/schemas/annotation.py` | Pydanticスキーマ定義 |
| Frontend | `frontend/annotation-tool/src/pages/ListPage.tsx` | 一覧画面 |
| Frontend | `frontend/annotation-tool/src/pages/AnnotationPage.tsx` | 詳細画面 |
| Frontend | `frontend/annotation-tool/src/types/api.ts` | 型定義 |
| Frontend | `frontend/annotation-tool/src/api/client.ts` | APIクライアント |
| Data | `master/flowering_date.csv` | 各地点の開花・満開予想日 |
| Data | `master/260121_bloom_state.csv` | **新規** 都道府県別ステータス開始日 |

#### 既存パターン
- **レイヤードアーキテクチャ**: interfaces → application → domain ← infrastructure
- **サービスパターン**: シングルトン + ファクトリ関数（`get_xxx_service()`）
- **SQLAlchemy Mapped型**: 明示的型定義
- **Alembicマイグレーション**: カラム追加 + インデックス作成パターンあり

### 1.2 既存の開花状態計算ロジック

`annotation_detail.py:186-226`に簡易版の実装が存在:

```python
def _calculate_bloom_status(...) -> str | None:
    if photo < flowering:
        return "開花前"
    elif photo < flowering + timedelta(days=3):
        return "3分咲き"
    elif full_bloom_start and photo < full_bloom_start:
        return "5分咲き"
    elif full_bloom_start and full_bloom_end and flowering <= photo <= full_bloom_end:
        return "満開"
    elif full_bloom_end and photo <= full_bloom_end + timedelta(days=3):
        return "散り始め"
    else:
        return "葉桜"
```

**ギャップ:**
- 要件の8ステータス（開花前、開花、3分咲き、5分咲き、8分咲き（満開）、散り始め、花＋若葉、葉のみ）と不一致
- 固定オフセット（3日など）を使用しており、都道府県別オフセットに非対応
- `260121_bloom_state.csv`のパース機能がない

### 1.3 データ構造分析

#### `260121_bloom_state.csv`フォーマット
```csv
No.,都道府県,開花,3分咲き,5分咲き,8分咲き（満開）,散り始め,花＋若葉（葉桜）,葉のみ
01,北海道函館市,4月21日,4月22日,4月24日,4月26日,5月1日,5月6日,5月11日
02,青森県青森市,4月17日,4月19日,4月20日,4月22日,4月27日,5月2日,5月7日
```

#### オフセット計算要件
要件より、各都道府県について以下を計算:
1. 開花→3分咲きオフセット = 3分咲き開始日 - 開花開始日
2. 開花→5分咲きオフセット = 5分咲き開始日 - 開花開始日
3. 散り始め→花＋若葉オフセット = 花＋若葉開始日 - 散り始め開始日
4. 散り始め→葉のみオフセット = 葉のみ開始日 - 散り始め開始日

### 1.4 既存フィルター実装

一覧APIは既に複数フィルターをサポート:
- `status`: all / annotated / unannotated
- `prefecture_code`: 都道府県コード
- `vitality_value`: 元気度
- `photo_date_from/to`: 撮影日範囲
- `is_ready`: 準備完了フラグ

フィルター適用パターンが確立されており、bloom_statusフィルターの追加は既存パターンに従える。

---

## 2. 要件別実装可能性分析

| 要件 | 技術的ニーズ | ギャップ | 複雑性 |
|---|---|---|---|
| R1: 開花状態計算ロジック | 新サービス実装、CSVパース | 既存ロジックを全面刷新 | 中 |
| R2: DBスキーマ拡張 | Alembicマイグレーション | パターン確立済み | 低 |
| R3: バッチ更新スクリプト | 新規スクリプト作成 | 類似スクリプトあり | 低 |
| R4: API拡張 | フィルター追加、統計拡張 | 既存パターン踏襲 | 低 |
| R5: 詳細画面改善 | レスポンス改善 | 既に部分対応済み | 低 |
| R6: フロントエンド一覧 | フィルターUI、統計表示 | 類似実装あり | 低 |
| R7: フロントエンド詳細 | 表示改善 | 既に部分対応済み | 低 |

---

## 3. 実装アプローチオプション

### オプションA: 既存コンポーネント拡張

**概要:** FloweringDateServiceを拡張して新CSVをパースし、annotation_detail.pyの_calculate_bloom_statusを改善

**対象ファイル:**
- `app/domain/services/flowering_date_service.py` - CSVパース追加
- `app/application/annotation/annotation_detail.py` - ロジック改善
- `app/application/annotation/annotation_list.py` - フィルター・統計追加

**トレードオフ:**
- ✅ 既存ファイル数を維持
- ❌ FloweringDateServiceの責務が拡大しすぎる
- ❌ annotation_detail.pyにビジネスロジックが集中

### オプションB: 新規コンポーネント作成

**概要:** BloomStatusServiceを新規作成し、完全に分離された開花状態判定機能を提供

**新規ファイル:**
- `app/domain/services/bloom_status_service.py` - 8ステータス判定サービス
- `app/domain/models/bloom_state_data.py` - CSVデータモデル
- `scripts/update_bloom_status.py` - バッチ更新スクリプト
- `migrations/versions/xxx_add_bloom_status_column.py` - マイグレーション

**トレードオフ:**
- ✅ 責務の明確な分離
- ✅ テスト容易性
- ❌ ファイル数増加
- ❌ FloweringDateServiceとの連携設計が必要

### オプションC: ハイブリッドアプローチ（推奨）

**概要:**
- 新規BloomStatusServiceを作成（8ステータス判定の中核ロジック）
- FloweringDateServiceは既存維持（既存コードへの影響最小化）
- annotation_list.py/annotation_detail.pyは既存パターンで拡張

**実装戦略:**
1. **Phase 1 - ドメイン層**
   - BloomStatusService新規作成（260121_bloom_state.csvパース + オフセット計算）
   - EntireTreeモデルにbloom_statusカラム追加（マイグレーション）

2. **Phase 2 - バッチ処理**
   - update_bloom_status.pyスクリプト作成
   - 既存データの一括更新

3. **Phase 3 - API拡張**
   - annotation_list.pyにbloom_statusフィルター・統計追加
   - annotation_detail.pyは既存bloom_status表示を維持（DBから取得に変更）

4. **Phase 4 - フロントエンド**
   - 型定義・APIクライアント更新
   - 一覧画面にフィルターUI・統計表示追加
   - 詳細画面の色分け・バッジ改善

**トレードオフ:**
- ✅ 責務の明確な分離
- ✅ 既存コードへの影響最小化
- ✅ 段階的実装可能
- ❌ 新規ファイル追加（ただし適切な粒度）

---

## 4. 実装複雑性とリスク

### 工数見積もり

| コンポーネント | 工数 | 根拠 |
|---|---|---|
| BloomStatusService | M | CSVパース + 8ステータス判定ロジック |
| DBマイグレーション | S | 既存パターン踏襲 |
| バッチスクリプト | S | 単純なループ処理 |
| API拡張 | S | 既存フィルターパターン踏襲 |
| フロントエンド拡張 | M | UI追加 + 状態管理 |

**総合工数: M（3-7日）**

### リスク評価

| リスク | レベル | 理由 | 緩和策 |
|---|---|---|---|
| 260121_bloom_state.csv フォーマット変更 | 低 | 既存パターンあり | 柔軟なパーサー設計 |
| 大量データの一括更新 | 低 | バッチサイズ指定可能 | dry-runモード実装 |
| 沖縄県等のデータ欠損 | 低 | 要件でNULL許容明記 | 適切なNULLハンドリング |
| フロントエンド互換性 | 低 | 追加のみで既存壊さない | 後方互換API設計 |

**総合リスク: Low**

---

## 5. 設計フェーズへの推奨事項

### 採用アプローチ
**オプションC: ハイブリッドアプローチ**を推奨

### 設計フェーズで要調査事項

1. **BloomStatusService設計**
   - 260121_bloom_state.csvのパースロジック詳細
   - 都道府県コードとCSV行のマッピング方法
   - オフセット計算の境界条件（年跨ぎ等）

2. **バッチ処理設計**
   - トランザクション戦略（バッチサイズ、ロールバック）
   - エラーハンドリング戦略（継続処理 vs 中断）
   - 進捗表示フォーマット

3. **API設計**
   - bloom_statusフィルターの複数指定方法（配列 vs カンマ区切り）
   - 統計レスポンスの構造（ネスト vs フラット）

4. **フロントエンドUI設計**
   - フィルターUIのレイアウト（ドロップダウン vs チップ）
   - ステータス別色分けの定義
   - 統計情報の表示レイアウト

---

## 6. 既存アセットマップ

```
Requirements → Existing Asset → Gap
─────────────────────────────────────────────────────
R1 開花状態計算 → flowering_date_service.py → 260121_bloom_state.csv未対応、オフセット計算なし
R2 DBスキーマ → models.py → bloom_statusカラムなし
R3 バッチスクリプト → (なし) → 新規作成
R4 API拡張 → annotation.py → bloom_statusフィルターなし、統計なし
R5 詳細画面 → annotation_detail.py → bloom_status計算済み（改善必要）
R6 一覧画面 → ListPage.tsx → bloom_statusフィルターUI・統計なし
R7 詳細画面 → AnnotationPage.tsx → bloom_status表示済み（色分け改善必要）
```

---

## 次のステップ

1. 本Gap分析をレビュー
2. `/kiro:spec-design bloom-status-filter` を実行してテクニカルデザイン作成
3. 設計承認後、`/kiro:spec-tasks bloom-status-filter` でタスク生成

# Research & Design Decisions

## Summary
- **Feature**: bloom-status-filter
- **Discovery Scope**: Extension（既存のアノテーションツールへの機能追加）
- **Key Findings**:
  - 既存の `_calculate_bloom_status` は簡略化されたロジックで、requirements で求められる8段階の詳細なステータス判定に対応していない
  - 260121_bloom_state.csv から都道府県別のオフセット値を計算する新しいサービスが必要
  - EntireTree に bloom_status カラムを追加し、インデックスを付与する必要がある

## Research Log

### 既存の開花状態計算ロジック分析
- **Context**: 現在のアノテーション詳細画面で bloom_status が表示されているが、要件で求められる8段階のステータスに対応しているか確認
- **Sources Consulted**: `app/application/annotation/annotation_detail.py:186-227`
- **Findings**:
  - 現行ロジックは6段階（開花前、3分咲き、5分咲き、満開、散り始め、葉桜）で判定
  - 固定オフセット（3日）を使用しており、都道府県別のオフセット計算に対応していない
  - 「開花」ステータス（開花開始直後）と「8分咲き（満開）」「花＋若葉（葉桜）」「葉のみ」の区別がない
- **Implications**:
  - requirements で定義された8段階のステータスに対応する新しい計算ロジックが必要
  - 都道府県別オフセット計算のためのデータソースとサービスを新規実装

### CSVデータソース分析
- **Context**: 開花状態計算に必要なデータソースの構造確認
- **Sources Consulted**:
  - `master/flowering_date.csv`: 各地点の開花予想日、満開開始日、満開終了日
  - `master/260121_bloom_state.csv`: 都道府県代表地点の各ステータス開始日
- **Findings**:
  - `flowering_date.csv`: 緯度経度ベースで最寄り地点の開花予想日を取得（既存の `FloweringDateService` で対応済み）
  - `260121_bloom_state.csv`: 47都道府県の代表地点について、8ステータスの開始日を保持
    - カラム: 都道府県, 開花, 3分咲き, 5分咲き, 8分咲き（満開）, 散り始め, 花＋若葉（葉桜）, 葉のみ
    - 沖縄県はすべて "-"（データなし）
  - オフセット計算例（青森県）:
    - 開花日: 4/17
    - 3分咲き開始日: 4/19 → 開花→3分咲きオフセット = 2日
    - 5分咲き開始日: 4/20 → 開花→5分咲きオフセット = 3日
    - 満開開始日: 4/22（flowering_date.csv から取得）
    - 散り始め開始日: 4/27 → 満開終了→散り始め終了オフセット = 5日（満開終了日を4/26とすると）
- **Implications**:
  - 新しい `BloomStateService` を作成し、260121_bloom_state.csv を読み込んでオフセット計算を行う
  - FloweringDateService と連携して最終的なステータスを判定

### データベーススキーマ設計
- **Context**: フィルタリング・ソートパフォーマンスのためのカラム追加
- **Sources Consulted**:
  - `app/domain/models/models.py`: EntireTree モデル定義
  - `app/domain/models/annotation.py`: VitalityAnnotation モデル定義
- **Findings**:
  - EntireTree には photo_date, censorship_status などのフィルタリング用カラムが既にインデックス付きで存在
  - VitalityAnnotation に is_ready フラグが追加されている（先行実装）
  - bloom_status は EntireTree に追加が妥当（撮影情報と密接に関連）
- **Implications**:
  - `bloom_status` カラム（VARCHAR(20), NULL許容, インデックス付き）を EntireTree に追加
  - Alembic マイグレーションで追加

### フロントエンド構成分析
- **Context**: 既存UIへの統合方法の確認
- **Sources Consulted**:
  - `frontend/annotation-tool/src/pages/ListPage.tsx`
  - `frontend/annotation-tool/src/pages/AnnotationPage.tsx`
  - `frontend/annotation-tool/src/types/api.ts`（推定）
- **Findings**:
  - ListPage: ステータスフィルター（STATUS_TABS）、is_readyフィルター（IS_READY_TABS）のパターンが既に存在
  - 統計情報表示エリアが存在し、拡張可能
  - AnnotationPage: bloom_status の表示と色分けは既に実装済み（getBloomStatusStyle関数）
  - フィルター状態はURLパラメータで管理
- **Implications**:
  - bloom_status フィルターは既存のパターン（タブ or ドロップダウン）に従って追加
  - 8つのステータスはドロップダウン形式が適切（タブには多すぎる）
  - 統計情報エリアにステータス別件数を追加

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| A: 既存サービス拡張 | FloweringDateService を拡張して bloom_status 計算を追加 | 既存パターン踏襲、変更範囲が限定的 | 責務が混在する可能性 | - |
| B: 新規サービス追加 | BloomStateService を新規作成し、オフセット計算を担当 | 責務の明確な分離、テスト容易 | ファイル数増加 | **採用** |
| C: ドメインモデル拡張 | EntireTree エンティティにロジックを追加 | ActiveRecord パターンとの親和性 | モデルが肥大化 | - |

**選択理由**: B案を採用。既存のレイヤードアーキテクチャに従い、ドメインサービスとして独立させることで、テスト容易性と責務の分離を確保。

## Design Decisions

### Decision: bloom_status カラムの配置
- **Context**: フィルタリング・ソートのパフォーマンス確保
- **Alternatives Considered**:
  1. EntireTree に追加 — 撮影情報との関連性が高い
  2. VitalityAnnotation に追加 — アノテーション関連情報との一貫性
  3. 計算値としてリアルタイム算出 — カラム追加不要
- **Selected Approach**: EntireTree に bloom_status カラムを追加
- **Rationale**:
  - bloom_status は photo_date と location から決定される属性であり、EntireTree の責務範囲
  - VitalityAnnotation はアノテーション作業に関する情報（ユーザー入力値、is_ready）を管理
  - リアルタイム算出はクエリ時のパフォーマンスに影響
- **Trade-offs**:
  - データ更新時に bloom_status の再計算が必要
  - CSVデータ変更時に一括更新スクリプトの再実行が必要
- **Follow-up**: マイグレーション後に既存データのバッチ更新を実行

### Decision: ステータス値の表現方法
- **Context**: 8つのステータス値をどのように保存するか
- **Alternatives Considered**:
  1. VARCHAR(20) — 日本語文字列をそのまま保存
  2. ENUM型 — DB制約で値を限定
  3. VARCHAR(20) — 英語キーを保存し、UIで日本語に変換
- **Selected Approach**: VARCHAR(20) で英語キーを保存、UIで日本語ラベルに変換
- **Rationale**:
  - 言語に依存しないDB設計
  - 短い文字列でインデックス効率向上
  - 国際化対応が容易
  - コードでの比較が簡潔（`status == "full_bloom"` vs `status == "8分咲き（満開）"`）
- **Trade-offs**:
  - UI表示時にマッピング処理が必要（定数定義で対応）
  - 既存の AnnotationPage のロジック変更が必要
- **Follow-up**: バックエンド・フロントエンド両方に `BLOOM_STATUS_LABELS` 定数を定義

**BloomStatus 値マッピング**:
| DB値（英語） | UI表示（日本語） |
|-------------|-----------------|
| `before_bloom` | 開花前 |
| `blooming` | 開花 |
| `30_percent` | 3分咲き |
| `50_percent` | 5分咲き |
| `full_bloom` | 8分咲き（満開） |
| `falling` | 散り始め |
| `with_leaves` | 花＋若葉（葉桜） |
| `leaves_only` | 葉のみ |

### Decision: バッチ更新スクリプトの設計
- **Context**: 既存データへの bloom_status 一括設定
- **Alternatives Considered**:
  1. Alembic マイグレーション内で実行 — 自動化されるがマイグレーション時間が長くなる
  2. 独立スクリプト — 柔軟な実行タイミング、進捗表示可能
  3. 管理コマンド — FastAPI CLI との統合
- **Selected Approach**: 独立したCLIスクリプトとして実装
- **Rationale**:
  - ドライランモード、バッチサイズ指定、進捗表示といった運用要件への対応
  - 将来的なデータ変更時の再実行が容易
  - テスト環境での部分実行が可能
- **Trade-offs**:
  - マイグレーションと別途実行が必要
  - 実行順序の管理が必要
- **Follow-up**: スクリプトを `scripts/` ディレクトリに配置

## Risks & Mitigations
- **Risk 1**: 都道府県の特定が失敗するケース（prefecture_code がNULL、または緯度経度から判定できない）
  - **Mitigation**: bloom_status を NULL にして「未設定」として扱う（requirements 1.12, 1.13 に対応）

- **Risk 2**: 沖縄県など bloom_state.csv にデータがない都道府県
  - **Mitigation**: 該当都道府県は bloom_status を NULL として扱う（requirements 1.13 に対応）

- **Risk 3**: 年をまたぐ撮影日のケース（1月撮影で開花日が4月）
  - **Mitigation**: 撮影年を基準に開花予想日の年を調整（既存の FloweringDateService のパターンに従う）

## References
- [既存 FloweringDateService 実装](app/domain/services/flowering_date_service.py)
- [SQLAlchemy 2.0 Mapped型ドキュメント](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html#using-annotated-declarative-table-type-annotated-forms-for-mapped-column)
- [Alembic マイグレーションガイド](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

# ギャップ分析: 全景バリデーション (sakura-fullview-validation)

## 分析サマリー

- **スコープ**: 桜の元気度判定パイプラインに AWS Bedrock マルチモーダル LLM による全景バリデーション工程を追加。デバッグ API・ページも合わせて実装
- **主な課題**: Bedrock 連携がコードベースに存在しない（新規 AWS サービス統合）。プロンプトエンジニアリングと構造化 JSON 出力の設計が必要
- **既存活用**: レイヤードアーキテクチャ、`aioboto3` パターン、デバッグ API テンプレート、例外体系がすべて再利用可能
- **複雑度**: M（3〜7日）。既存パターン踏襲で主要部分は実装可能だが、Bedrock 連携と LLM プロンプト調整に工数を要する
- **リスク**: 中。Bedrock の Converse API の利用経験なし（要リサーチ）、LLM 判定精度はプロンプト品質依存

---

## 1. 要件からアセットへのマッピング

### Requirement 1: 全景バリデーション判定ロジック

| 技術的ニーズ | 既存アセット | ギャップ |
|---|---|---|
| Bedrock マルチモーダルモデル呼び出し | `aioboto3` パターン（`label_detector.py`, `image_service.py`） | **Missing**: Bedrock クライアント連携が未実装 |
| OK/NG 判定結果の返却 | `ApplicationError` パターン（`exceptions.py`） | 拡張可能 |
| 判定理由テキスト | なし | **Missing**: LLM レスポンス解析ロジック |
| 信頼度スコア (0.0〜1.0) | なし | **Missing**: LLM にスコア出力を要求するプロンプト設計 |

### Requirement 2: NG 判定条件の定義

| 技術的ニーズ | 既存アセット | ギャップ |
|---|---|---|
| NG パターン（枝先端のみ、クローズアップ等）の判定 | なし | **Missing**: プロンプトに条件を組み込む設計 |
| 一貫した判定基準 | なし | **Missing**: プロンプトテンプレートの定義 |

### Requirement 3: パイプライン統合

| 技術的ニーズ | 既存アセット | ギャップ |
|---|---|---|
| Rekognition 後・元気度解析前の実行位置 | `create_tree.py` L124-131（ラベル検出後） | 拡張可能。L131 の後に全景バリデーション呼び出しを追加 |
| NG 時のエラーレスポンス（理由・信頼度含む） | `ApplicationError` 基盤、`error_handlers.py` | 新しい例外クラス追加（`FullviewValidationError` 等） |
| 元気度解析をスキップ | `create_tree.py` の制御フロー | 拡張可能。例外 raise で後続処理をスキップ |

### Requirement 4: 全景バリデーション専用デバッグ API

| 技術的ニーズ | 既存アセット | ギャップ |
|---|---|---|
| POST エンドポイント | `debug.py` ルーター（既存パターン完全流用可能） | 新規エンドポイント追加 |
| Basic 認証 | `auth_utils.py` の `get_current_username()` | そのまま利用可能 |
| JSON レスポンス（OK/NG, 理由, 信頼度） | `debug.py` のスキーマパターン | 新規 Pydantic スキーマ追加 |

### Requirement 5: デバッグページ機能追加

| 技術的ニーズ | 既存アセット | ギャップ |
|---|---|---|
| `tree_analysis.html` への全景バリデーション結果表示 | テンプレート（432行、桜テーマ UI） | テーブルに行追加で拡張可能 |
| 全景バリデーション専用 HTML ページ | `tree_analysis.html` / `stem_analysis.html` テンプレートパターン | 新規テンプレート作成（既存パターン踏襲） |

### Requirement 6: Bedrock 連携

| 技術的ニーズ | 既存アセット | ギャップ |
|---|---|---|
| Converse API / InvokeModel API 呼び出し | `aioboto3` セットアップパターン（`label_detector.py`） | **Missing**: `bedrock-runtime` クライアント初期化 |
| エラーハンドリング・ログ | `loguru` ロギング、`ApplicationError` 例外 | 拡張可能 |
| モデル ID 環境変数化 | 環境変数パターン（`AI_API_ENDPOINT`, `AWS_REGION` 等） | 新規環境変数追加 |
| プロンプト定義・JSON 構造化出力 | なし | **Missing**: プロンプトテンプレートと出力パースロジック |

---

## 2. 実装アプローチオプション

### Option A: 既存コンポーネント拡張

**概要**: `ai_service.py` に Bedrock 呼び出しメソッドを追加し、`create_tree.py` のパイプラインに統合

- **拡張対象ファイル**:
  - `app/domain/services/ai_service.py` — `validate_fullview()` メソッド追加
  - `app/application/tree/create_tree.py` — バリデーション呼び出し追加
  - `app/application/debug/analyze_tree.py` — 全景バリデーション結果追加
  - `app/interfaces/api/debug.py` — 新規エンドポイント追加
  - `app/interfaces/schemas/debug.py` — 新規レスポンススキーマ追加
  - `app/interfaces/templates/tree_analysis.html` — 結果テーブル拡張
  - `app/application/exceptions.py` — 新規例外クラス追加

**トレードオフ**:
- ✅ 既存の `AIService` シングルトンパターンに自然に統合
- ✅ ファイル数最小限（新規テンプレート1つのみ新規作成）
- ❌ `ai_service.py` が REST API と Bedrock API の2種の外部連携を持つことになり責務肥大化
- ❌ Bedrock クライアント管理（セッション、リージョン）が `ai_service.py` に混在

### Option B: 新規コンポーネント作成

**概要**: 全景バリデーション専用のサービスを独立ドメインサービスとして作成

- **新規作成ファイル**:
  - `app/domain/services/fullview_validation_service.py` — Bedrock 連携・判定ロジック
  - `app/application/debug/validate_fullview.py` — デバッグ用アプリケーションロジック
  - `app/interfaces/schemas/fullview_validation.py` — レスポンススキーマ
  - `app/interfaces/templates/fullview_validation.html` — 専用デバッグページ

- **拡張対象ファイル**:
  - `app/application/tree/create_tree.py` — バリデーション呼び出し追加
  - `app/interfaces/api/debug.py` — 新規エンドポイント追加
  - `app/interfaces/templates/tree_analysis.html` — 結果テーブル拡張
  - `app/application/exceptions.py` — 新規例外クラス追加

**トレードオフ**:
- ✅ 単一責務の原則に沿った設計（Bedrock 連携を独立管理）
- ✅ 独立テスト・モック化が容易
- ✅ プロンプトの変更や将来のモデル差し替えが容易
- ❌ ファイル数増加
- ❌ DI 配線の追加（`get_fullview_validation_service()` ファクトリ関数）

### Option C: ハイブリッドアプローチ

**概要**: Bedrock クライアントをインフラ層に配置し、ドメインサービスとして全景バリデーションを独立

- **新規作成ファイル**:
  - `app/infrastructure/bedrock/bedrock_client.py` — Bedrock クライアントラッパー（`label_detector.py` と同階層構造）
  - `app/domain/services/fullview_validation_service.py` — 判定ロジック（インフラ層の Bedrock クライアントを利用）
  - `app/application/debug/validate_fullview.py` — デバッグ用ロジック
  - `app/interfaces/schemas/fullview_validation.py` — レスポンススキーマ
  - `app/interfaces/templates/fullview_validation.html` — 専用デバッグページ

- **拡張対象ファイル**: Option B と同じ

**トレードオフ**:
- ✅ レイヤードアーキテクチャに最も忠実（Bedrock = 外部サービス → インフラ層）
- ✅ `label_detector.py`（Rekognition）と同じパターンで一貫性が高い
- ✅ Bedrock クライアントの再利用性が高い（将来の他機能でも使用可能）
- ❌ ファイル数が最も多い
- ❌ 現状では Bedrock を使うのはこの機能のみのため、やや過剰設計の可能性

---

## 3. 工数・リスク評価

### 工数: **M（3〜7日）**

- Bedrock クライアント連携は `aioboto3` パターン踏襲で1日程度
- プロンプト設計・調整に1〜2日（判定精度に直結）
- パイプライン統合・デバッグ API・テンプレートは既存パターン踏襲で2〜3日
- テスト作成に1日

### リスク: **中**

- **Bedrock Converse API**: コードベースに使用実績なし。`aioboto3` で `bedrock-runtime` を扱う際の非同期パターンをリサーチする必要あり（**Research Needed**）
- **LLM 判定精度**: プロンプト品質に大きく依存。NG/OK の境界ケースでの一貫性は反復テストが必要
- **構造化 JSON 出力**: LLM が常に期待通りの JSON を返す保証はない。パースエラー時のフォールバック設計が必要（**Research Needed**: Bedrock の structured output / tool use 機能の調査）
- **レイテンシ**: LLM 呼び出しがパイプラインに追加されるため、元気度判定全体の応答時間が増加。並列実行の検討が必要

---

## 4. リサーチ項目（設計フェーズで調査）

1. **Bedrock Converse API の `aioboto3` での利用方法**: 非同期呼び出しパターン、画像データの送信方法（Base64 vs バイト列）
2. **Bedrock 構造化出力機能**: JSON フォーマットでの出力強制方法（tool use、response format 指定等）
3. **使用モデル選定**: Claude Sonnet vs Claude Haiku vs Nova のコスト・レイテンシ・精度のバランス
4. **プロンプト設計**: 全景判定の具体的なプロンプトテンプレート、JSON 出力スキーマの定義
5. **レイテンシ最適化**: 全景バリデーションを Rekognition / AI 解析と並列実行可能かの検討

---

## 5. デザインフェーズへの推奨事項

### 推奨アプローチ: **Option B（新規コンポーネント作成）**

**理由**:
- Bedrock 連携は既存の AI サービス（REST API ベース）とは本質的に異なる外部サービス統合であり、独立サービスとして管理すべき
- プロンプトの反復改善やモデル差し替えが独立して行えるため、運用フェーズでのメンテナンスが容易
- 既存の `create_tree.py` への変更は最小限（バリデーション呼び出し追加のみ）
- Option C のインフラ層分離は将来 Bedrock の利用が拡大した段階でリファクタリングすればよく、初期段階では不要

### キー決定事項
1. Bedrock Converse API vs InvokeModel API の選択（リサーチ後に決定）
2. 全景バリデーションを元気度解析と並列実行するか、直列実行するか
3. LLM のレスポンスが JSON パース不可能な場合のフォールバック戦略
4. 環境変数設計（モデル ID、リージョン等）

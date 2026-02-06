# Research & Design Decisions

## Summary
- **Feature**: `sakura-fullview-validation`
- **Discovery Scope**: Extension（既存の元気度判定パイプラインへの新バリデーション段階の追加）
- **Key Findings**:
  - AWS Bedrock Converse API が最推奨。boto3 で統一的なインターフェースが利用可能
  - 既存パイプラインの Rekognition ラベル検出後、元気度解析前に全景バリデーションを挿入可能
  - 構造化 JSON 出力には `toolConfig` によるツール呼び出しパターンが最も信頼性が高い

## Research Log

### AWS Bedrock Converse API vs InvokeModel API
- **Context**: 全景バリデーションでマルチモーダル LLM を呼び出す最適な API の選定
- **Sources Consulted**: AWS Bedrock 公式ドキュメント、boto3 リファレンス
- **Findings**:
  - Converse API はモデル間で統一的なインターフェースを提供し、モデル変更時のコード修正が不要
  - InvokeModel API はモデル固有のリクエスト形式が必要で保守コストが高い
  - Converse API は画像入力（multimodal）を標準サポート
  - boto3 SDK が自動的に base64 エンコーディングを処理
- **Implications**: Converse API を採用。将来のモデル変更に対する柔軟性を確保

### 利用可能な Claude モデルとリージョン制約
- **Context**: Bedrock 上で利用可能なマルチモーダル対応 Claude モデルと東京リージョンでの利用可否の確認
- **Sources Consulted**: AWS Bedrock モデルカタログ、リージョン別モデルサポートページ、クロスリージョン推論ドキュメント
- **Findings**:
  - Claude Sonnet 4.5 以降のモデルは東京リージョン（ap-northeast-1）にネイティブデプロイされていない
  - **クロスリージョン推論プロファイル経由で利用可能**:
    - APAC プロファイル: `apac.anthropic.claude-sonnet-4-5-20250929-v1:0`（推奨。データが APAC 圏内に留まる）
    - Global プロファイル: `global.anthropic.claude-sonnet-4-5-20250929-v1:0`（データが APAC 外に出る可能性あり）
  - APAC ルーティング先: ap-northeast-1/2/3, ap-south-1/2, ap-southeast-1/2（7 リージョン）
  - Haiku 4.5: `apac.anthropic.claude-haiku-4-5-20251001-v1:0`（低コスト代替）
- **Implications**: デフォルトモデル ID は `apac.anthropic.claude-sonnet-4-5-20250929-v1:0` を使用。環境変数 `BEDROCK_MODEL_ID` で変更可能にする

### Bedrock モデルアクセス申請
- **Context**: 既存 AWS アカウントで Bedrock Claude モデルを利用するための追加手続きの確認
- **Sources Consulted**: AWS Bedrock モデルアクセスドキュメント、AWS Security Blog
- **Findings**:
  - Anthropic Claude モデルには **一度だけユースケース情報の提出が必要**
  - 提出先: Bedrock コンソール → Model catalog → Anthropic モデル選択 → ユースケースフォーム
  - 必要情報: 会社名、Web サイト、利用者（社内/社外）、業種、ユースケース説明
  - **即時自動承認**（人手レビューなし）、費用なし
  - 一度有効化すれば同アカウント内の全 IAM ユーザーが利用可能、全サポートリージョンに適用
  - IAM 権限: `aws-marketplace:Subscribe` 等が必要（`AmazonBedrockFullAccess` ポリシー推奨）
- **Implications**: 実装開始前に Bedrock コンソールからモデルアクセス申請を完了しておく必要がある（前提条件としてドキュメントに記載）

### 構造化 JSON 出力の方法
- **Context**: LLM からの判定結果を確実に JSON 形式で取得する方法
- **Sources Consulted**: AWS Bedrock Structured Output ドキュメント、Converse API toolConfig リファレンス
- **Findings**:
  - 方法 1: `toolConfig` によるツール呼び出し — スキーマ定義に沿った構造化出力を強制可能
  - 方法 2: `outputConfig.textFormat` による JSON スキーマ指定 — より新しいアプローチだが互換性確認が必要
  - 方法 3: プロンプトエンジニアリング — 信頼性が低い
- **Implications**: `toolConfig` パターンを採用。ツール定義として判定結果のスキーマを指定し、信頼性の高い構造化出力を実現

### 画像フォーマットとサイズ制限
- **Context**: Converse API の画像入力制約の確認
- **Sources Consulted**: AWS Bedrock API リファレンス、Claude Vision ドキュメント
- **Findings**:
  - 対応フォーマット: JPEG, PNG, GIF, WebP
  - 最大ファイルサイズ: 3.75 MB
  - 最大解像度: 8000x8000 px
  - 画像トークン計算: `(width × height) / 750`
  - 長辺 1568px を超えると自動リサイズ
- **Implications**: 既存パイプラインで EXIF 回転済み・JPEG 変換済みの画像データをそのまま利用可能。サイズ制限内に収まることを確認する処理は不要（既存画像は通常この範囲内）

### 既存パイプラインの統合ポイント分析
- **Context**: `create_tree.py` の処理フローにおける全景バリデーションの挿入位置
- **Sources Consulted**: `app/application/tree/create_tree.py`（行 123-131）
- **Findings**:
  - 現在のフロー: 画像前処理 → Rekognition ラベル検出（Tree/Person） → 画像アップロード＋AI解析 → DB登録
  - Rekognition による `Tree` ラベル検出（行 125-131）の後が最適な挿入位置
  - ラベル検出で木が確認された画像に対してのみ全景バリデーションを実行（不要な API 呼び出しを回避）
  - 全景バリデーションが NG の場合、後続の画像アップロード・AI 解析・DB 登録をスキップ
- **Implications**: Rekognition ラベル検出後、`asyncio.gather` による並列処理の前に全景バリデーションを実行

### 既存デバッグエンドポイントパターン
- **Context**: デバッグ API の構造パターンの確認
- **Sources Consulted**: `app/interfaces/api/debug.py`, `app/interfaces/templates/tree_analysis.html`
- **Findings**:
  - JSON API: `POST /debug/{function}` — `response_model` で型指定
  - HTML フォーム: `GET /debug/{function}_html` でフォーム表示、`POST /debug/{function}_html` で結果表示
  - 認証: HTML エンドポイントは `Depends(get_current_username)` で Basic 認証
  - テンプレート: Jinja2、共通スタイル（桜色テーマ）、ローディングオーバーレイ
  - サービス注入: `Depends(get_xxx_service, use_cache=True)` パターン
- **Implications**: 同一パターンに従い、3 エンドポイント（JSON API、HTML GET、HTML POST）を追加

### エラーハンドリングパターン
- **Context**: 全景バリデーション NG 時のエラー返却方式
- **Sources Consulted**: `app/application/exceptions.py`, `app/interfaces/api/error_handlers.py`
- **Findings**:
  - `ApplicationError` を基底クラスとする例外階層
  - 各例外は `reason`, `error_code`, `status`, `details` を持つ
  - グローバルエラーハンドラーが JSONResponse に変換
  - 既存の類似例外: `TreeNotDetectedError`（error_code=101）
- **Implications**: `FullviewValidationError` を新設。`error_code` はプロジェクト内でユニークな番号を割り当て、`details` に判定理由と信頼度を含める

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| 既存レイヤード拡張 | 既存の domain/services に FullviewValidationService を追加 | 既存パターンとの一貫性、実装コスト低 | なし | 採用 |
| 独立マイクロサービス | 全景バリデーションを別サービスとして分離 | 独立スケーリング | 過剰設計、デプロイ複雑化 | 不採用 |

## Design Decisions

### Decision: Converse API + toolConfig による構造化出力
- **Context**: LLM から判定結果を確実に構造化された形式で取得する必要がある
- **Alternatives Considered**:
  1. `toolConfig` — ツール定義として JSON スキーマを指定
  2. `outputConfig.textFormat` — JSON スキーマ指定
  3. プロンプトエンジニアリングのみ — テキストから JSON をパース
- **Selected Approach**: `toolConfig` によるツール呼び出しパターン
- **Rationale**: Bedrock 上の Claude モデルで最も広くサポートされ、スキーマに沿った出力を強制可能。パース失敗のリスクが最小
- **Trade-offs**: toolConfig 使用時はレスポンス構造が通常のテキスト出力と異なるため、レスポンス解析ロジックが専用になる
- **Follow-up**: ツール定義のスキーマが判定品質に影響しないか実運用で検証

### Decision: 全景バリデーションの挿入位置
- **Context**: 元気度判定パイプラインのどの段階で全景バリデーションを実行するか
- **Alternatives Considered**:
  1. Rekognition ラベル検出の前 — 木でない画像にも Bedrock API を呼び出してしまう
  2. Rekognition ラベル検出の後、元気度解析の前 — 木と確認された画像のみ対象
  3. 元気度解析と並列実行 — NG 時に不要な解析コストが発生
- **Selected Approach**: Rekognition ラベル検出の後、元気度解析の前（逐次実行）
- **Rationale**: 木と確認された画像のみに Bedrock API を呼び出すことで API コストを最適化。NG 時は早期リターンで後続処理をスキップ
- **Trade-offs**: パイプライン全体のレイテンシが Bedrock API 呼び出し分（1-3秒）増加
- **Follow-up**: レイテンシが問題になる場合、キャッシュや並列実行を検討

### Decision: 新規 FullviewValidationService の配置
- **Context**: 新サービスを既存アーキテクチャのどの層に配置するか
- **Alternatives Considered**:
  1. `domain/services/` — ドメインサービスとして配置
  2. `infrastructure/` — 外部サービス連携として配置
- **Selected Approach**: `domain/services/fullview_validation_service.py` として配置
- **Rationale**: 既存の `AIService` と同じ層に配置し、一貫性を維持。Bedrock API 呼び出しはドメインロジック（判定基準のプロンプト定義）と密結合しているため、ドメイン層が適切
- **Trade-offs**: 純粋なクリーンアーキテクチャでは外部 API 呼び出しはインフラ層が望ましいが、既存パターンとの一貫性を優先
- **Follow-up**: なし

## Risks & Mitigations
- **Bedrock API レイテンシ**: マルチモーダル解析は 1-3 秒かかる可能性 → パイプライン全体のタイムアウト設定を確認・調整
- **Bedrock API コスト**: 画像トークン + 出力トークンで 1 回あたり約 $0.01 → モデル選択（Haiku vs Sonnet）で調整可能にする
- **LLM 判定の不安定性**: 同一画像でも判定結果が変動する可能性 → 信頼度の閾値設定で境界ケースを管理、temperature を低く設定
- **Bedrock API 障害**: サービス障害時にパイプライン全体が停止 → エラー時はログ記録の上、バリデーションをスキップ（フェイルオープン）して後続処理を継続

## References
- [AWS Bedrock Converse API ドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html)
- [boto3 Bedrock Runtime converse メソッド](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html)
- [Bedrock 構造化出力](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)
- [Claude Vision ドキュメント](https://platform.claude.com/docs/en/build-with-claude/vision)

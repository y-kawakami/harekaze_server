# 全景バリデーション Bedrock ランニングコスト分析

## 概要

全景バリデーション機能では、AWS Bedrock の Claude Sonnet 4.5 を使用して、
桜画像が全景撮影（樹木全体が写っている）かどうかを判定する。
本ドキュメントでは、1リクエストあたりのコストおよび月間コストの試算を行う。

## 前提条件

| 項目 | 値 |
|---|---|
| モデル | Claude Sonnet 4.5 (`apac.anthropic.claude-sonnet-4-5-20250929-v1:0`) |
| エンドポイント | APAC cross-region inference profile（Regional 扱い、10%プレミアム） |
| 入力画像サイズ | 2048x2048 px（1:1） |
| API 呼び出し方式 | Bedrock Converse API + Tool Use（forced） |
| 1バリデーションあたりの API コール数 | 1回 |

## 料金体系

### Bedrock と Anthropic API の料金関係

Claude Sonnet 4.5 の**ベーストークン単価は Bedrock と Anthropic API で同一**である。
ただし、Bedrock では エンドポイントの種類によって料金が異なる。

| エンドポイント | 説明 | 料金 |
|---|---|---|
| Anthropic API | Anthropic 直接利用（Global のみ） | ベース料金 |
| Bedrock Global endpoint（`global.*`） | リージョンを跨いで動的ルーティング | ベース料金（Anthropic API と同額） |
| Bedrock Cross-region endpoint（`us.*`, `eu.*`, `apac.*`） | 指定地域内でのルーティングを保証 | **ベース料金 + 10%** |

> **本実装への影響**: `apac.anthropic.claude-sonnet-4-5-20250929-v1:0` は
> APAC cross-region inference profile のため、**10%プレミアムが適用される**。
> データレジデンシー要件がなければ `global.*` プレフィクスの inference profile に
> 切り替えることで 10% のコスト削減が可能。

### Claude Sonnet 4.5 トークン単価

| エンドポイント種別 | Input | Output |
|---|---|---|
| Anthropic API / Bedrock Global | $3.00 / MTok | $15.00 / MTok |
| Bedrock Cross-region / APAC（+10%） | **$3.30 / MTok** | **$16.50 / MTok** |

> MTok = 100万トークン
>
> 参考:
> - https://platform.claude.com/docs/en/about-claude/pricing
> - https://aws.amazon.com/bedrock/pricing/

### 画像トークン算出方法

Claude Vision では画像は自動的にトークンに変換される。
トークン数の計算式は以下の通り:

```
tokens = (width px × height px) / 750
```

ただし、長辺が 1568px を超える場合、または画像が約 1,600 トークンを超える場合、
アスペクト比を維持したまま自動的にリサイズされる。

> 参考: https://platform.claude.com/docs/en/build-with-claude/vision

## トークン数の算出

### 画像トークン

入力画像: **2048x2048 px**（アスペクト比 1:1）

- 長辺 2048px > 1568px のため自動リサイズが発生
- 1:1 アスペクト比の最大サイズ: **1092x1092 px**（公式テーブル値）
- 画像トークン数: `(1092 × 1092) / 750 ≒ 1,590 トークン`

### リクエスト全体のトークン内訳

| 項目 | トークン数 | 備考 |
|---|---|---|
| 画像（リサイズ後 1092x1092） | ~1,590 | `(1092×1092)/750` |
| システムプロンプト | ~60 | 専門家ペルソナ指示（約45語） |
| ユーザープロンプト | ~300 | OK/NG 条件の詳細指示（約234語） |
| Tool Use システムオーバーヘッド | 313 | forced tool choice 時の固定値 |
| ツール定義（スキーマ） | ~150 | `fullview_validation` ツール定義 |
| **Input 合計** | **~2,413** | |
| **Output（JSON レスポンス）** | **~150** | `is_valid`, `reason`, `confidence` |

## 1リクエストあたりのコスト

### APAC endpoint（10%プレミアム込み）

```
Input:  2,413 tokens / 1,000,000 × $3.30  = $0.00796
Output:   150 tokens / 1,000,000 × $16.50 = $0.00248
─────────────────────────────────────────────────────
合計: $0.01044 / リクエスト（約 1.6円 @155円/USD）
```

### Global endpoint（参考）

```
Input:  2,413 tokens / 1,000,000 × $3.00  = $0.00724
Output:   150 tokens / 1,000,000 × $15.00 = $0.00225
─────────────────────────────────────────────────────
合計: $0.00949 / リクエスト（約 1.5円 @155円/USD）
```

## 月間コスト試算

### APAC endpoint 使用時

| 日次リクエスト数 | 月間リクエスト数 | 月間コスト（USD） | 月間コスト（JPY） |
|---|---|---|---|
| 10 | 300 | $3.13 | 約 490円 |
| 50 | 1,500 | $15.66 | 約 2,430円 |
| 100 | 3,000 | $31.32 | 約 4,850円 |
| 300 | 9,000 | $93.96 | 約 14,560円 |
| 500 | 15,000 | $156.60 | 約 24,270円 |
| 667 | 20,000 | $208.80 | 約 32,360円 |
| 1,000 | 30,000 | $313.20 | 約 48,550円 |

> JPY 換算レート: 1 USD = 155 JPY（2025年参考値）

## コスト最適化オプション

### 1. Haiku 4.5 への切り替え

| 項目 | Sonnet 4.5（APAC） | Haiku 4.5（APAC） |
|---|---|---|
| Input | $3.30 / MTok | $1.10 / MTok |
| Output | $16.50 / MTok | $5.50 / MTok |
| **1リクエストあたり** | **$0.01044** | **$0.00348** |
| コスト削減率 | - | **約 67% 削減** |

精度要件を満たせる場合、Haiku 4.5 への切り替えで大幅なコスト削減が可能。

### 2. Prompt Caching

システムプロンプトとツール定義をキャッシュすることで、リクエスト間で共通部分のコストを削減できる。

- キャッシュ書き込み: 1.25倍（5分間キャッシュ）
- キャッシュヒット: **0.1倍**（通常の1/10）
- 対象トークン: システムプロンプト(~60) + ツールオーバーヘッド(313) + ツール定義(~150) = ~523 トークン

高頻度アクセス時に有効だが、本機能の対象トークン数が少ないため効果は限定的。

### 3. Batch API（非リアルタイム処理の場合）

- 全トークン **50% 割引**
- 1リクエストあたり: $0.00522（約 0.8円）
- リアルタイムバリデーションでは使用不可

## エンドポイント種別ごとのレイテンシ・スループット比較

### レイテンシ（応答速度）

| エンドポイント種別 | ルーティング先 | 追加レイテンシ |
|---|---|---|
| 単一リージョン | そのリージョンのみ | なし（最も低レイテンシ） |
| APAC cross-region（`apac.*`） | APAC 内 7 リージョン | 数十ミリ秒（APAC 内ルーティング） |
| Global（`global.*`） | 全世界の商用リージョン | 最大で数百ミリ秒（米国・欧州等へのルーティングの可能性） |

- cross-region inference は可能な限りソースリージョン（東京）を優先するが、負荷が高い場合は他リージョンにルーティングされる
- LLM 推論自体が 1〜3 秒かかるため、ルーティングによる追加レイテンシ（数十〜数百 ms）は全体に対して軽微

### スループット（処理能力）

利用可能なリージョン数が多いほどスループットが高くなる。

```
Global（全リージョン） > Geographic / APAC（7リージョン） > 単一リージョン
```

- **Global**: 全世界のリソースを活用。最も高いスループット
- **APAC**: APAC 圏内のリソースを活用。ピーク時のスロットリング耐性は Global より低い
- **単一リージョン**: そのリージョンのサービスクォータに制限される

### APAC プロファイルのルーティング先

`ap-northeast-1`（東京）からリクエストした場合のルーティング候補:

| リージョン | 所在地 |
|---|---|
| ap-northeast-1 | 東京（優先） |
| ap-northeast-2 | ソウル |
| ap-northeast-3 | 大阪 |
| ap-south-1 | ムンバイ |
| ap-south-2 | ハイデラバード |
| ap-southeast-1 | シンガポール |
| ap-southeast-2 | シドニー |

### Global プロファイルのルーティング先

`ap-northeast-1`（東京）からリクエストした場合、全世界の商用 AWS リージョンがルーティング候補となる。
米国・欧州リージョンに処理が回る可能性がある。

- Global inference profile ID: `global.anthropic.claude-sonnet-4-5-20250929-v1:0`

### エンドポイント選択の指針

| 優先事項 | 推奨エンドポイント |
|---|---|
| コスト最小化 | Global（10% 安い） |
| レイテンシの安定性 | APAC（APAC 内に限定されるため予測可能） |
| スループット最大化 | Global（全リージョンのリソース活用） |
| データレジデンシー（地域内処理保証） | APAC |

> **本プロジェクトの判断**: 桜画像は個人情報や機密データではないため、
> データレジデンシー要件は基本的にない。
> 全景バリデーションの処理時間は 1〜3 秒であり、ルーティングによる追加レイテンシは
> 体感上の差はほぼない。コスト重視なら Global、レイテンシ安定性重視なら APAC が適切。

> 参考:
> - https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html
> - https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html

## 注意事項

- 上記のトークン数は推定値であり、実際の値は画像内容やレスポンス内容により変動する
- 為替レートは変動するため、定期的な見直しが必要
- Bedrock の料金体系は変更される可能性がある（最新情報は AWS 公式ページを確認）
- NG 判定時の S3 保存コストは別途発生する（本ドキュメントの対象外）

## 参考リンク

- [Claude Pricing - Anthropic](https://platform.claude.com/docs/en/about-claude/pricing)
- [Claude Vision Documentation](https://platform.claude.com/docs/en/build-with-claude/vision)
- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Cross-Region Inference - Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html)
- [Supported Regions and models for inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html)

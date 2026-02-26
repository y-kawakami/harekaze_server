# Requirements Document

## Project Description (Input)
POST sakura_camera/api/tree/entire の更新。従来は開花状況に応じて枝のみ・満開モデルをブレンドしていたが、新たに bloom_30_percent（3分咲き）、bloom_50_percent（5分咲き）の AI API が追加。location と日時から枝のみ・3分咲き・5分咲き・満開を判断し適切なモデルで判定。開花状態の判定は bloom-status-filter の開花状態計算フローに近いが、get_prefecture_offsets のオフセットを開花予想日〜満開開始予想日の比で補正して適用。満開から1週間は満開モデルと枝のみモデルをブレンド。

## Introduction

本仕様は `POST /sakura_camera/api/tree/entire` エンドポイントにおける樹勢判定ロジックの多段階化を定義する。従来の2モデル（枝のみ・満開）ブレンド方式から、4段階の開花モデル（枝のみ・3分咲き・5分咲き・満開）を使い分ける方式へ拡張し、撮影場所と日時に基づいて最適なAIモデルを選択する。

## Requirements

### Requirement 1: 開花段階判定ロジック
**Objective:** As a システム, I want 撮影場所（緯度・経度）と撮影日時から現在の開花段階を判定したい, so that 適切なAIモデルを選択し、精度の高い樹勢診断を行える

#### Acceptance Criteria
1. When `create_tree` が緯度・経度・撮影日時を受け取った時, the 樹勢判定サービス shall `FloweringDateService.find_nearest_spot()` を使用して最寄りの開花予想スポットを取得する
2. When 最寄りスポットの開花予想日（flowering_date）と満開開始予想日（full_bloom_date）が取得できた時, the 樹勢判定サービス shall 撮影日がどの開花段階に該当するかを以下の6段階で判定する: 枝のみ（開花前・葉桜期）、開花ブレンド、3分咲き、5分咲き、満開、満開後ブレンド
3. When 開花段階を判定する時, the 樹勢判定サービス shall `BloomStateService.get_prefecture_offsets()` から取得したオフセット値を「開花予想日〜満開開始予想日」の期間比で補正して適用する
4. When 撮影日が開花予想日より前の時, the 樹勢判定サービス shall 開花段階を「枝のみ」と判定する
5. When 撮影日が開花予想日から補正済み3分咲きオフセット日までの期間内の時, the 樹勢判定サービス shall 開花段階を「開花ブレンド期間」と判定する（枝のみモデルと3分咲きモデルの線形ブレンド）
6. When 撮影日が補正済み3分咲きオフセット日から補正済み5分咲きオフセット日までの期間内の時, the 樹勢判定サービス shall 開花段階を「3分咲き」と判定する
7. When 撮影日が補正済み5分咲きオフセット日から満開開始予想日までの期間内の時, the 樹勢判定サービス shall 開花段階を「5分咲き」と判定する
8. When 撮影日が満開開始予想日から満開終了予想日までの期間内の時, the 樹勢判定サービス shall 開花段階を「満開」と判定する
9. When 撮影日が満開終了予想日から10日以内の時, the 樹勢判定サービス shall 開花段階を「満開後ブレンド期間」と判定する
10. When 撮影日が満開終了予想日から10日を超えた時, the 樹勢判定サービス shall 開花段階を「枝のみ」と判定する

### Requirement 2: オフセット補正計算
**Objective:** As a システム, I want 都道府県ごとのオフセット値を開花予想日〜満開開始予想日の比率で補正したい, so that 地域差を反映した正確な開花段階判定が行える

#### Acceptance Criteria
1. The 樹勢判定サービス shall 基準となるオフセット値（`flowering_to_3bu`、`flowering_to_5bu`）を `BloomStateService.get_prefecture_offsets()` から取得する
2. When オフセット補正を行う時, the 樹勢判定サービス shall 最寄りスポットの「開花予想日から満開開始予想日までの実日数」と「基準オフセットが前提とする開花〜満開期間」の比率を算出する
3. When 比率が算出できた時, the 樹勢判定サービス shall `flowering_to_3bu` と `flowering_to_5bu` にその比率を乗じて補正済みオフセット（日数）を算出する
4. If 都道府県コードに対応するオフセットが存在しない時, then the 樹勢判定サービス shall オフセット補正を適用せずにフォールバック動作を行う

### Requirement 3: マルチステージAIモデル呼び出し
**Objective:** As a システム, I want 判定された開花段階に応じて適切なAI樹勢診断モデルを呼び出したい, so that 開花状態に最適化された樹勢判定結果が得られる

#### Acceptance Criteria
1. When 開花段階が「枝のみ」と判定された時, the AIサービス shall 枝のみモデル（`/analyze/image/vitality/noleaf`）を呼び出して樹勢を判定する
2. When 開花段階が「3分咲き」と判定された時, the AIサービス shall 3分咲きモデル（`/analyze/image/vitality/bloom_30_percent`）を呼び出して樹勢を判定する
3. When 開花段階が「5分咲き」と判定された時, the AIサービス shall 5分咲きモデル（`/analyze/image/vitality/bloom_50_percent`）を呼び出して樹勢を判定する
4. When 開花段階が「満開」と判定された時, the AIサービス shall 満開モデル（`/analyze/image/vitality/bloom`）を呼び出して樹勢を判定する
5. The AIサービス shall 各モデルの呼び出し結果として vitality（1〜5の整数）と vitality_real（浮動小数点）を返却する

### Requirement 4: ブレンドロジック
**Objective:** As a システム, I want 開花初期と満開終了後の遷移期間において2つのモデル結果をブレンドしたい, so that 開花段階の境界付近での樹勢判定精度を確保できる

#### Acceptance Criteria
1. When 開花段階が「開花ブレンド期間」と判定された時, the 樹勢判定サービス shall 枝のみモデルと3分咲きモデルの両方を呼び出す
2. When 開花ブレンド期間内の時, the 樹勢判定サービス shall 開花予想日からの経過日数に応じてブレンド比率を線形補間で算出する（開花直後: 枝のみモデル寄り → 補正済み3分咲きオフセット日: 3分咲きモデル寄り）
3. When 開花段階が「満開後ブレンド期間」と判定された時, the 樹勢判定サービス shall 満開モデルと枝のみモデルの両方を呼び出す
4. When 満開後ブレンド期間内の時, the 樹勢判定サービス shall 満開終了日からの経過日数に応じてブレンド比率を線形補間で算出する（満開終了直後: 満開モデル寄り → 10日後: 枝のみモデル寄り）
5. When ブレンド比率が算出された時, the 樹勢判定サービス shall 最終的な vitality_real を `model_a_result.vitality_real * weight_a + model_b_result.vitality_real * weight_b` で算出する
6. When ブレンド結果が算出された時, the 樹勢判定サービス shall vitality_real を四捨五入して vitality（1〜5整数）を算出する

### Requirement 5: 判定結果の保存
**Objective:** As a システム, I want 新しい多段階モデルの判定結果をデータベースに保存したい, so that 後続の分析・アノテーション作業で判定根拠を参照できる

#### Acceptance Criteria
1. The 樹勢判定サービス shall 最終的なブレンド済み vitality と vitality_real を EntireTree レコードに保存する
2. The 樹勢判定サービス shall 使用したモデルの種類と各モデルの判定結果（vitality、vitality_real）を EntireTree レコードに保存する
3. The 樹勢判定サービス shall 適用したブレンド重みを EntireTree レコードに保存する
4. When 開花段階が単一モデルで判定された時（ブレンドなし）, the 樹勢判定サービス shall 使用モデルの重みを 1.0、未使用モデルの重みを 0.0 として保存する

### Requirement 6: エラーハンドリングとフォールバック
**Objective:** As a システム, I want 開花情報やAIモデルが利用できない場合にも安全に動作したい, so that サービスの可用性を維持できる

#### Acceptance Criteria
1. If 最寄りの開花予想スポットが見つからない時, then the 樹勢判定サービス shall 従来と同じ2モデルブレンド方式（`estimate_vitality` による季節ベースの重み算出）にフォールバックする
2. If 都道府県コードが取得できずオフセット補正が不可能な時, then the 樹勢判定サービス shall 従来の `estimate_vitality` 方式にフォールバックする
3. If 3分咲きモデルまたは5分咲きモデルのAPI呼び出しが失敗した時, then the AIサービス shall エラーをログに記録し、エラーレスポンスを返却する（異常時の検出を優先するため、フォールバックは行わない）
4. If いずれかのAIモデル呼び出しがタイムアウトした時, then the AIサービス shall 既存のリトライロジックに従って再試行する

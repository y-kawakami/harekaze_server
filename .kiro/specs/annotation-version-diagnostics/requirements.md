# Requirements Document

## Project Description (Input)

アノテーション画面に変更を加えたい。

- アノテーションのトップ画面に 2025年度, 2026年度というチェックボックスをつける
  - チェックを入れた期間のもののみが表示される
  - どちらの期間かは trees に version カラムを入れる
    - version: デフォルト 202501
    - 新規で作成されるもの: 202601
- 詳細画面(/annotation/{tree_id})に以下追加
  - 木登録 API と同じ方法で算出した、3分咲き、5分咲きの日(開花日と満開開始日の間)

上記に加えて、Admin権限のみ詳細画面で EntireTree の以下を表示

- (診断モデルによる)診断値
  - 元気度(vitality)
  - 花なし元気度(vitality_noleaf)
  - vitality_noleaf_weight
  - vitality_bloom
  - vitality_bloom_weight
  - vitality_bloom_30
  - vitality_bloom_30_weight
  - vitality_bloom_50
  - vitality_bloom_50_weight
- 元気度 vitality でフィルタ可能

また、詳細画面から別画面で、デバッグ表示も行い、以下のようなセグメンテーション画像も表示したい。

- entire_debug_noleaf_(uid).jpg
- entire_debug_bloom_(uid).jpg

## Introduction

本仕様は、アノテーション機能に対する以下の拡張を定義する:

1. **年度バージョンフィルタ**: アノテーショントップ画面に年度チェックボックスを追加し、対象期間のデータのみ表示可能にする
2. **開花段階日表示**: アノテーション詳細画面に3分咲き・5分咲きの算出日を表示する
3. **診断値表示（Admin限定）**: 詳細画面でEntireTreeの診断モデル出力値をAdmin権限ユーザーに表示する
4. **元気度フィルタ（Admin限定）**: 診断値の元気度（vitality）でフィルタリングを可能にする
5. **デバッグ画像表示（Admin限定）**: 詳細画面からセグメンテーション画像を別画面で確認可能にする

## Requirements

### Requirement 1: 年度バージョンカラム追加

**Objective:** As a 開発者, I want treesテーブルにversionカラムを追加したい, so that 年度ごとにデータを区別できる

#### Acceptance Criteria

1. The Annotation API shall treesテーブルにinteger型の`version`カラムを持つ
2. While 既存レコードにversionが未設定の場合, the Annotation API shall デフォルト値として`202501`を設定する
3. When 新規にtreeが作成される場合, the Annotation API shall versionに`202601`を設定する

### Requirement 2: 年度フィルタUI

**Objective:** As a アノテーター, I want アノテーショントップ画面で年度チェックボックスにより表示データを絞り込みたい, so that 対象期間のデータのみを効率的に確認できる

#### Acceptance Criteria

1. The Annotation API shall アノテーショントップ画面に「2025年度」「2026年度」のチェックボックスを提供する
2. When ユーザーが「2025年度」チェックボックスを選択した場合, the Annotation API shall version=202501のtreeのみを返却する
3. When ユーザーが「2026年度」チェックボックスを選択した場合, the Annotation API shall version=202601のtreeのみを返却する
4. When ユーザーが両方のチェックボックスを選択した場合, the Annotation API shall 両方のversionのtreeを返却する
5. If どちらのチェックボックスも選択されていない場合, the Annotation API shall 全てのtreeを返却する

### Requirement 3: 開花段階日表示

**Objective:** As a アノテーター, I want アノテーション詳細画面で3分咲き・5分咲きの日を確認したい, so that 開花状態の進行を把握できる

#### Acceptance Criteria

1. The Annotation API shall アノテーション詳細画面（/annotation/{tree_id}）にEntireTreeモデルの`bloom_30_date`（3分咲き日）と`bloom_50_date`（5分咲き日）を表示する
2. If EntireTreeに`bloom_30_date`・`bloom_50_date`が記録されていない場合, the Annotation API shall 該当項目を空欄として表示する

### Requirement 4: 診断値表示（Admin限定）

**Objective:** As a Admin権限ユーザー, I want アノテーション詳細画面でEntireTreeの診断モデル出力値を確認したい, so that 診断結果の妥当性を検証できる

#### Acceptance Criteria

1. While ユーザーがAdmin権限を持つ場合, the Annotation API shall アノテーション詳細画面にEntireTreeの以下の診断値を表示する: vitality, vitality_noleaf, vitality_noleaf_weight, vitality_bloom, vitality_bloom_weight, vitality_bloom_30, vitality_bloom_30_weight, vitality_bloom_50, vitality_bloom_50_weight
2. While ユーザーがAdmin権限を持たない場合, the Annotation API shall 診断値セクションを表示しない
3. The Annotation API shall 各診断値をEntireTreeモデルから取得して表示する

### Requirement 5: 元気度フィルタ（Admin限定）

**Objective:** As a Admin権限ユーザー, I want 元気度（vitality）でデータをフィルタしたい, so that 特定の元気度範囲のデータを効率的に確認できる

#### Acceptance Criteria

1. While ユーザーがAdmin権限を持つ場合, the Annotation API shall 元気度（vitality）によるフィルタ機能を提供する
2. When Admin権限ユーザーがvitalityフィルタ値を指定した場合, the Annotation API shall 指定されたvitality値に一致するtreeのみを返却する
3. While ユーザーがAdmin権限を持たない場合, the Annotation API shall vitalityフィルタ機能を表示しない

### Requirement 6: デバッグ画像表示（Admin限定）

**Objective:** As a Admin権限ユーザー, I want アノテーション詳細画面からセグメンテーション画像を確認したい, so that AI診断のデバッグ情報を視覚的に確認できる

#### Acceptance Criteria

1. While ユーザーがAdmin権限を持つ場合, the Annotation API shall アノテーション詳細画面にデバッグ画像表示へのリンクを提供する
2. When Admin権限ユーザーがデバッグ画像表示リンクをクリックした場合, the Annotation API shall 別画面で以下のセグメンテーション画像を表示する: `entire_debug_noleaf_{uid}.jpg`, `entire_debug_bloom_{uid}.jpg`
3. If 対象のデバッグ画像が存在しない場合, the Annotation API shall 画像が存在しない旨を表示する
4. While ユーザーがAdmin権限を持たない場合, the Annotation API shall デバッグ画像表示リンクを表示しない


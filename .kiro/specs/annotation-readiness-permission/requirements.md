# Requirements Document

## Project Description (Input)
.kiro/specs/sakura-vitality-annotation でアノテーションツールを作成しましたが、
あらかじめアノテーターに提供する画像を選別するため、評価対象としてチェックしておく仕組みが必要です.
vitality_annotations テーブルに is_ready フラグを追加し、このフラグの True/False で絞り込みを行えるようにし、また、アノテーション画面で、このチェックを変更できるようにしてください。
また、annotators の権限を増やし、この is_ready をON/OFFできるかどうかと、is_ready の変更と表示ができる権限と、その他の通常のアノテーターの権限を分けてほしいです。
また、通常のアノテーターは、is_ready のもののみ表示できるようにもしたいです。

## Introduction

本仕様は、既存のアノテーションシステムに「評価準備完了」(is_ready) フラグと権限管理機能を追加するものです。これにより、管理者がアノテーション対象画像を事前選別し、一般アノテーターには準備完了した画像のみを提供できるようになります。

## Requirements

### Requirement 1: データモデル拡張
**Objective:** As a システム管理者, I want 画像ごとに評価準備完了状態を記録できる, so that アノテーターに提供する画像を事前に選別できる

#### Acceptance Criteria
1. The vitality_annotations table shall have an `is_ready` column of BOOLEAN type with default value FALSE
2. When 画像にアノテーションが保存される, the Annotation API shall `is_ready` フラグを変更せず既存の値を保持する
3. The vitality_annotations table shall maintain an index on `is_ready` column for efficient filtering

### Requirement 2: アノテーター権限モデル
**Objective:** As a システム管理者, I want アノテーターごとに異なる権限を設定できる, so that 役割に応じた機能制限ができる

#### Acceptance Criteria
1. The annotators table shall have a `role` column of VARCHAR type to store the annotator's role
2. The Annotation System shall support the following roles:
   - `admin`: すべての画像を表示、`is_ready` の変更・アノテーション実行が可能
   - `annotator`: `is_ready=TRUE` の画像のみ表示、アノテーション実行のみ可能
3. When 新しいアノテーターが作成される, the system shall assign the default role as `annotator`
4. The Annotation System shall validate role values and reject invalid role assignments

### Requirement 3: 権限による画像一覧フィルタリング
**Objective:** As a アノテーター, I want 自分の権限に応じた画像のみを表示したい, so that 適切な作業範囲で効率的にアノテーションできる

#### Acceptance Criteria
1. When `annotator` ロールのユーザーが画像一覧を取得する, the Annotation API shall `is_ready=TRUE` の画像のみを返す
2. When `admin` ロールのユーザーが画像一覧を取得する, the Annotation API shall すべての画像を返す
3. While `admin` ロールでログイン中, the Annotation API shall `is_ready` フィルターパラメータによる絞り込みを許可する
4. The Annotation API shall return 403 Forbidden when `annotator` ロールが `is_ready=FALSE` の画像を直接アクセスしようとした場合

### Requirement 4: is_ready フラグの変更API
**Objective:** As a 管理者権限アノテーター, I want 画像の is_ready フラグを変更したい, so that アノテーション対象画像を管理できる

#### Acceptance Criteria
1. When `admin` ロールのユーザーが is_ready 変更リクエストを送信する, the Annotation API shall 指定された画像の `is_ready` フラグを更新する
2. If `annotator` ロールのユーザーが is_ready 変更を試みた場合, the Annotation API shall 403 Forbidden エラーを返す
3. When is_ready フラグが変更される, the Annotation API shall 変更後の画像情報を含むレスポンスを返す
4. The Annotation API shall support batch update of is_ready flag for multiple images

### Requirement 5: フロントエンド一覧画面の拡張
**Objective:** As a 管理者権限アノテーター, I want 一覧画面で is_ready 状態を確認・変更したい, so that 効率的に画像を選別できる

#### Acceptance Criteria
1. While `admin` ロールでログイン中, the Annotation UI shall 各画像に `is_ready` 状態を示すバッジを表示する
2. While `admin` ロールでログイン中, the Annotation UI shall `is_ready` フィルターオプション（全て/準備完了/未準備）を表示する
3. While `admin` ロールでログイン中, the Annotation UI shall 画像の `is_ready` 状態をワンクリックで切り替えるトグルを提供する
4. When `annotator` ロールでログイン中, the Annotation UI shall `is_ready` 関連のフィルターとトグルを非表示にする
5. When `admin` ロールが is_ready トグルをクリックした, the Annotation UI shall 即座にAPIを呼び出し状態を更新する

### Requirement 6: フロントエンド詳細画面の拡張
**Objective:** As a 管理者権限アノテーター, I want 詳細画面でも is_ready 状態を確認・変更したい, so that アノテーション作業中に画像の準備状態を調整できる

#### Acceptance Criteria
1. While `admin` ロールでログイン中, the Annotation Detail Page shall 現在の `is_ready` 状態を表示する
2. While `admin` ロールでログイン中, the Annotation Detail Page shall `is_ready` 状態を切り替えるトグルを提供する
3. When `annotator` ロールでログイン中, the Annotation Detail Page shall `is_ready` 関連のUI要素を非表示にする
4. When is_ready が変更される, the Annotation Detail Page shall 保存成功メッセージを表示する

### Requirement 7: 統計情報の拡張
**Objective:** As a 管理者権限アノテーター, I want is_ready 状態ごとの統計を確認したい, so that 選別作業の進捗を把握できる

#### Acceptance Criteria
1. While `admin` ロールでログイン中, the Annotation API shall `is_ready=TRUE` と `is_ready=FALSE` の件数を統計情報に含める
2. When `annotator` ロールが統計情報を取得する, the Annotation API shall `is_ready=TRUE` の画像のみを対象とした統計を返す
3. The Annotation UI shall 権限に応じた統計情報を一覧画面に表示する

### Requirement 8: 認証レスポンスの拡張
**Objective:** As a フロントエンド開発者, I want ログイン時に権限情報を取得したい, so that 権限に応じたUI制御ができる

#### Acceptance Criteria
1. When アノテーターがログインする, the Annotation API shall レスポンスにアノテーターの `role` を含める
2. When `/annotation_api/me` エンドポイントが呼び出される, the Annotation API shall 現在のアノテーターの `role` を含むレスポンスを返す
3. The Frontend Auth System shall ログイン後に取得した `role` をアプリケーション状態に保存する

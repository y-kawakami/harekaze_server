# Requirements Document

## Project Description (Input)
このプロジェクトで集まった桜の画像を使った再学習を行うために、現在S3にアップされている桜全体の画像に対してアノテーションを行うツールを開発したい。
アノテーションは、元気度を入力する。
- とっても元気(1)
- 元気(2)
- 普通(3)
- 少し気掛かり(4)
- 気掛かり(5)
ツールは web から入力を行う。画面構成は以下の通り。

## 一覧画面

- 桜一覧を表示
- 全て、アノテーション入力済み、未入力のタブでフィルタリング
- 都道府県でのフィルタリング
- 入力済みの項目を、さらに元気度(1-5)でフィルタリング
- 該当件数表示(入力済み・全て), 元気度(1-5) の入力件数

## アノテーション画面

- 一覧画面の項目をクリックするとアノテーション画面に遷移
- 構成要素( .kiro/specs/sakura-vitality-annotation/annotation_image.png 参照)
  - 評価する桜の写真
  - 元気度入力欄
    - とっても元気(1)
    - 元気(2)
    - 普通(3)
    - 少し気掛かり(4)
    - 気掛かり(5)
    - 診断不可(-1)
  - 戻る・次へボタン
  - 写真情報
    - 撮影日
    - 開花予想日
    - 満開開始予想日
    - 満開終了予想日
    - 都道府県
    - 撮影場所

## 現状のデータ情報

関連するテーブルは以下です。
- trees: ユーザ情報、撮影場所(location カラム)、perfecture_code( 都道府県コード)
- entire_trees: 桜全体画像情報。 対応する tree_id(treesテーブルのレコードのID)、image_obj_key(S3に保存されている画像)

S3のバケット名は(hrkz-prd-s3-contents)で、
画像オブジェクトのキーは、sakura_camera/media/trees/ に　image_obj_key を結合したものとなります。

また、開花状態については、entire_trees テーブルの、
 vitality_bloom_weight カラムで表され、以下ように分類されます。

0.2以上0.5未満: 3分咲き
0.5以上1.0未満: 5分咲き
1.0: 満開

DB へのアクセスは、パスワードは環境変数で与える形とし、ユーザは hrkz_user, DB名は hrkz_db  としてください。


## 新規に作成するテーブル

- アノテーション結果を格納するテーブル
  - アノテーション結果
  - アノテーション日時
  - アノテーター
- アノテーター情報
  - ユーザID
  - パスワード

## Requirements

### Requirement 1: アノテーター認証
**Objective:** As a アノテーター, I want ログインしてアノテーション作業を行う, so that 作業履歴と担当者が記録される

#### Acceptance Criteria
1. When アノテーターがログインフォームに正しいユーザIDとパスワードを入力する, the Annotation Tool shall 認証を行いセッションを開始する
2. If 無効なユーザIDまたはパスワードが入力された場合, the Annotation Tool shall エラーメッセージを表示しログインを拒否する
3. When アノテーターがログアウトボタンをクリックする, the Annotation Tool shall セッションを終了し、ログイン画面にリダイレクトする
4. While セッションが有効な間, the Annotation Tool shall アノテーション機能へのアクセスを許可する
5. If セッションが無効または期限切れの場合, the Annotation Tool shall ログイン画面にリダイレクトする

### Requirement 2: 桜一覧表示
**Objective:** As a アノテーター, I want S3に保存された桜全体画像の一覧を確認する, so that アノテーション対象を把握・選択できる

#### Acceptance Criteria
1. When アノテーターが一覧画面にアクセスする, the Annotation Tool shall entire_treesテーブルから桜全体画像の一覧を取得し表示する
2. The Annotation Tool shall 各一覧項目に桜のサムネイル画像、都道府県、撮影場所、アノテーション状態を表示する
3. The Annotation Tool shall 該当件数（全件数・入力済み件数）を表示する
4. The Annotation Tool shall 元気度(1-5)ごとの入力件数を表示する
5. When アノテーターが一覧項目をクリックする, the Annotation Tool shall 該当する桜のアノテーション画面に遷移する

### Requirement 3: 一覧フィルタリング
**Objective:** As a アノテーター, I want 一覧を条件でフィルタリングする, so that 効率的にアノテーション対象を絞り込める

#### Acceptance Criteria
1. When アノテーターが「全て」タブを選択する, the Annotation Tool shall 全ての桜画像を表示する
2. When アノテーターが「アノテーション入力済み」タブを選択する, the Annotation Tool shall アノテーション済みの桜画像のみを表示する
3. When アノテーターが「未入力」タブを選択する, the Annotation Tool shall アノテーション未入力の桜画像のみを表示する
4. When アノテーターが都道府県フィルターを選択する, the Annotation Tool shall 選択された都道府県の桜画像のみを表示する
5. While 「アノテーション入力済み」が選択されている間, the Annotation Tool shall 元気度(1-5)でのさらなるフィルタリングを可能にする
6. When フィルター条件が変更される, the Annotation Tool shall 該当件数表示を更新する

### Requirement 4: アノテーション入力
**Objective:** As a アノテーター, I want 桜画像に対して元気度を入力する, so that 再学習用のラベルデータを作成できる

#### Acceptance Criteria
1. When アノテーション画面を表示する, the Annotation Tool shall S3から対象の桜全体画像を取得し表示する
2. The Annotation Tool shall 元気度入力欄として以下の選択肢を表示する：とっても元気(1)、元気(2)、普通(3)、少し気掛かり(4)、気掛かり(5)、診断不可(-1)
3. When アノテーターが元気度を選択する, the Annotation Tool shall 選択状態を視覚的にハイライトする
4. When アノテーターが元気度を選択し確定する, the Annotation Tool shall アノテーション結果をデータベースに保存する
5. The Annotation Tool shall アノテーション保存時に、アノテーション日時とアノテーターIDを記録する
6. If 既にアノテーション済みの画像の場合, the Annotation Tool shall 既存のアノテーション値を初期選択状態で表示する

### Requirement 5: 撮影情報表示
**Objective:** As a アノテーター, I want 桜の撮影情報を確認する, so that 元気度判定の参考にできる

#### Acceptance Criteria
1. When アノテーション画面を表示する, the Annotation Tool shall 撮影日を表示する
2. When アノテーション画面を表示する, the Annotation Tool shall 開花予想日を表示する
3. When アノテーション画面を表示する, the Annotation Tool shall 満開開始予想日を表示する
4. When アノテーション画面を表示する, the Annotation Tool shall 満開終了予想日を表示する
5. When アノテーション画面を表示する, the Annotation Tool shall 都道府県名を表示する
6. When アノテーション画面を表示する, the Annotation Tool shall 撮影場所を表示する
7. The Annotation Tool shall 現在の診断枚数（進捗）を画面上部に表示する

### Requirement 6: アノテーションナビゲーション
**Objective:** As a アノテーター, I want 前後の桜画像に移動する, so that 連続してアノテーション作業を行える

#### Acceptance Criteria
1. When アノテーターが「次へ」ボタンをクリックする, the Annotation Tool shall 現在のフィルター条件内で次の桜画像のアノテーション画面に遷移する
2. When アノテーターが「戻る」ボタンをクリックする, the Annotation Tool shall 現在のフィルター条件内で前の桜画像のアノテーション画面に遷移する
3. If 最後の画像で「次へ」がクリックされた場合, the Annotation Tool shall 「次へ」ボタンを無効化するか、一覧画面に戻る
4. If 最初の画像で「戻る」がクリックされた場合, the Annotation Tool shall 「戻る」ボタンを無効化する
5. When 「データ一覧リストへ」リンクをクリックする, the Annotation Tool shall 一覧画面に戻る

### Requirement 7: データベース設計
**Objective:** As a システム, I want アノテーション結果を永続化する, so that 再学習に利用できる

#### Acceptance Criteria
1. The Annotation Tool shall アノテーション結果テーブルを作成し、entire_tree_id、元気度値、アノテーション日時、アノテーターIDを格納する
2. The Annotation Tool shall アノテーターテーブルを作成し、ユーザID、パスワード（ハッシュ化）を格納する
3. The Annotation Tool shall hrkz_user ユーザー、hrkz_db データベースを使用してDBに接続する
4. The Annotation Tool shall DBパスワードを環境変数から取得する
5. The Annotation Tool shall 元気度値として1-5および-1（診断不可）を許容する

### Requirement 8: S3画像連携
**Objective:** As a システム, I want S3から桜画像を取得する, so that アノテーション画面で表示できる

#### Acceptance Criteria
1. The Annotation Tool shall S3バケット「hrkz-prd-s3-contents」から画像を取得する
2. The Annotation Tool shall 画像オブジェクトキーを「sakura_camera/media/trees/」+「image_obj_key」で構成する
3. When 一覧画面で画像を表示する, the Annotation Tool shall サムネイルサイズで画像を表示する
4. When アノテーション画面で画像を表示する, the Annotation Tool shall 評価に適したサイズで画像を表示する
5. If S3から画像取得に失敗した場合, the Annotation Tool shall エラーを表示し、代替画像またはエラーメッセージを表示する

### Requirement 9: アノテーション結果CSVエクスポート
**Objective:** As a 開発者, I want アノテーション結果をCSV形式でダウンロードする, so that 再学習用データセットとして利用できる

#### Acceptance Criteria
1. When 一覧画面で「CSVエクスポート」ボタンをクリックする, the Annotation Tool shall アノテーション済みデータをCSV形式でダウンロードできる
2. The Annotation Tool shall 一覧画面にCSVエクスポートボタンを表示する
3. The Annotation Tool shall CSVに以下のカラムを含める：S3パス、画像ファイル名、スコア（元気度）
4. The Annotation Tool shall S3パスを「s3://hrkz-prd-s3-contents/sakura_camera/media/trees/{image_obj_key}」形式で出力する
5. The Annotation Tool shall 画像ファイル名を image_obj_key から抽出して出力する
6. The Annotation Tool shall スコアとしてアノテーションされた元気度値（1-5, -1）を出力する
7. The Annotation Tool shall 診断不可（-1）のデータも含めてエクスポートする

# Implementation Plan

## Task Overview

本実装計画は、アノテーションシステムに「評価準備完了」(is_ready) フラグと権限管理機能を追加するためのタスクを定義します。

---

## Tasks

- [x] 1. データベースマイグレーションの実装
- [x] 1.1 (P) annotators テーブルに role カラムを追加するマイグレーションを作成
  - 'admin' または 'annotator' の値を持つ VARCHAR(20) カラムを追加
  - デフォルト値を 'annotator' に設定
  - CHECK 制約で有効な role 値のみを許可
  - 既存レコードはデフォルト値が適用される
  - _Requirements: 2.1, 2.3_

- [x] 1.2 (P) vitality_annotations テーブルに is_ready カラムを追加するマイグレーションを作成
  - BOOLEAN 型の is_ready カラムを追加（DEFAULT FALSE）
  - vitality_value カラムを NULL 許容に変更（is_ready のみ設定時のため）
  - is_ready カラムにインデックスを作成してフィルタリング性能を確保
  - _Requirements: 1.1, 1.3_

- [x] 2. ドメインモデルの更新
- [x] 2.1 (P) Annotator モデルに role フィールドを追加
  - role フィールドを Mapped[str] として追加
  - 'admin' または 'annotator' のみ許可するバリデーションロジック
  - _Requirements: 2.1, 2.2, 2.4_

- [x] 2.2 (P) VitalityAnnotation モデルに is_ready フィールドを追加
  - is_ready フィールドを Mapped[bool] として追加（デフォルト FALSE）
  - vitality_value を Optional に変更
  - テーブル引数にインデックス定義を追加
  - _Requirements: 1.1, 1.3_

- [x] 3. 認証・認可機能の拡張
- [x] 3.1 AnnotationAuthService の JWT ペイロードに role を含める
  - トークン作成時に role をペイロードに追加
  - トークン検証時に role を抽出して返す
  - _Requirements: 2.4, 8.1, 8.2_

- [x] 3.2 管理者権限チェック用の require_admin 依存関数を作成
  - get_current_annotator で取得したアノテーターの role をチェック
  - admin 以外の場合は 403 Forbidden を返す
  - _Requirements: 4.2_

- [x] 3.3 認証 API のレスポンスに role を含める
  - ログインエンドポイントのレスポンスに role を追加
  - /me エンドポイントのレスポンスに role を追加
  - _Requirements: 8.1, 8.2_

- [ ] 4. Application 層のユースケース実装
- [ ] 4.1 is_ready フラグ更新ユースケースを実装
  - update_is_ready 関数を作成（単一画像の is_ready 更新）
  - VitalityAnnotation が存在しない場合は新規作成（vitality_value=NULL）
  - 更新後の情報を含むレスポンスを返す
  - _Requirements: 4.1, 4.3_

- [ ] 4.2 is_ready バッチ更新ユースケースを実装
  - update_is_ready_batch 関数を作成（複数画像の一括更新）
  - 更新件数と更新された ID リストを返す
  - _Requirements: 4.4_

- [ ] 4.3 annotation_list の権限ベースフィルタリングを実装
  - annotator ロールの場合、自動的に is_ready=TRUE でフィルター
  - admin ロールの場合、is_ready フィルターパラメータを任意で使用可能
  - 統計情報に is_ready 別の件数（ready_count, not_ready_count）を追加
  - _Requirements: 3.1, 3.2, 3.3, 7.1, 7.2_

- [ ] 4.4 annotation_detail の権限ベースアクセス制御を実装
  - annotator ロールが is_ready=FALSE の画像にアクセスした場合、PermissionError を発生
  - admin ロールはすべての画像にアクセス可能
  - 詳細レスポンスに is_ready フィールドを追加
  - _Requirements: 3.4_

- [ ] 4.5 save_annotation の is_ready 保持動作を確認
  - アノテーション保存時に is_ready フラグを変更しないことを確認
  - 必要に応じて既存の保存ロジックを調整
  - _Requirements: 1.2_

- [ ] 5. API エンドポイントの実装
- [ ] 5.1 is_ready 更新 API エンドポイントを追加
  - PATCH /annotation_api/trees/{id}/is_ready エンドポイントを作成
  - require_admin 依存関数で管理者権限を確認
  - リクエスト/レスポンススキーマを定義
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 5.2 is_ready バッチ更新 API エンドポイントを追加
  - PATCH /annotation_api/trees/is_ready/batch エンドポイントを作成
  - require_admin 依存関数で管理者権限を確認
  - バッチリクエスト/レスポンススキーマを定義
  - _Requirements: 4.4_

- [ ] 5.3 一覧 API のレスポンスを拡張
  - AnnotationListItemResponse に is_ready フィールドを追加
  - AnnotationStatsResponse に ready_count, not_ready_count を追加
  - is_ready_filter クエリパラメータを追加（admin のみ有効）
  - _Requirements: 3.1, 3.2, 3.3, 7.1, 7.2_

- [ ] 5.4 詳細 API のレスポンスを拡張
  - AnnotationDetailResponse に is_ready フィールドを追加
  - annotator ロールが is_ready=FALSE の画像にアクセスした場合、403 を返す
  - _Requirements: 3.4_

- [ ] 6. バックエンドテストの実装
- [ ] 6.1 (P) ドメインモデルのテストを追加
  - Annotator の role バリデーションテスト
  - VitalityAnnotation の is_ready デフォルト値テスト
  - _Requirements: 2.1, 2.2, 2.4, 1.1_

- [ ] 6.2 (P) 認証・認可機能のテストを追加
  - JWT ペイロードに role が含まれることを確認
  - require_admin が admin 以外で 403 を返すことを確認
  - /me エンドポイントが role を返すことを確認
  - _Requirements: 2.4, 4.2, 8.1, 8.2_

- [ ] 6.3 (P) is_ready 更新ユースケースのテストを追加
  - 新規作成時の動作（vitality_value=NULL）を確認
  - 更新時の動作を確認
  - バッチ更新の複数レコード処理を確認
  - _Requirements: 4.1, 4.3, 4.4_

- [ ] 6.4 (P) 権限ベースフィルタリングのテストを追加
  - annotator ロールで is_ready=TRUE のみ取得されることを確認
  - admin ロールで全件取得できることを確認
  - admin ロールで is_ready フィルターが動作することを確認
  - annotator ロールが is_ready=FALSE の詳細にアクセスで 403 を確認
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 7.1, 7.2_

- [ ] 7. フロントエンド型定義と API クライアントの更新
- [ ] 7.1 (P) 型定義を更新
  - Annotator 型に role フィールドを追加
  - AnnotationListItem 型に is_ready フィールドを追加
  - AnnotationStats 型に ready_count, not_ready_count を追加
  - AnnotationDetail 型に is_ready フィールドを追加
  - is_ready 更新用のリクエスト/レスポンス型を追加
  - _Requirements: 2.2, 5.1, 7.1_

- [ ] 7.2 (P) API クライアントに is_ready 更新関数を追加
  - updateIsReady 関数を追加（単一更新）
  - updateIsReadyBatch 関数を追加（バッチ更新）
  - _Requirements: 4.1, 4.4_

- [ ] 8. フロントエンド認証状態管理の拡張
- [ ] 8.1 useAuth フックに role 情報を追加
  - Annotator 型に role を反映
  - isAdmin ヘルパーを追加（annotator?.role === 'admin'）
  - ログイン時と /me 取得時に role を保存
  - _Requirements: 8.3_

- [ ] 9. 一覧画面（ListPage）の UI 更新
- [ ] 9.1 is_ready バッジ表示を実装
  - 各画像カードに is_ready 状態を示すバッジを表示
  - admin ロールの場合のみバッジを表示
  - _Requirements: 5.1, 5.4_

- [ ] 9.2 is_ready フィルターオプションを実装
  - 「全て」「準備完了」「未準備」のフィルター選択 UI を追加
  - admin ロールの場合のみフィルターを表示
  - フィルター変更時に一覧を再取得
  - _Requirements: 5.2, 5.4_

- [ ] 9.3 is_ready トグル機能を実装
  - 各画像カードに is_ready 切り替えトグルを追加
  - admin ロールの場合のみトグルを表示
  - トグルクリック時に即座に API を呼び出して状態を更新
  - 楽観的更新で UI を即時反映し、失敗時にロールバック
  - _Requirements: 5.3, 5.5_

- [ ] 9.4 統計情報の表示を拡張
  - ready_count, not_ready_count を統計表示に追加
  - admin ロールの場合は is_ready 別統計を表示
  - annotator ロールの場合は既存の統計のみ表示
  - _Requirements: 7.1, 7.2, 7.3_

- [ ] 10. 詳細画面（AnnotationPage）の UI 更新
- [ ] 10.1 is_ready 状態表示を追加
  - 撮影情報セクションに現在の is_ready 状態を表示
  - admin ロールの場合のみ表示
  - _Requirements: 6.1, 6.3_

- [ ] 10.2 is_ready トグルと保存メッセージを実装
  - is_ready 状態を切り替えるトグルを追加
  - admin ロールの場合のみトグルを表示
  - トグル操作時に API を呼び出して状態を更新
  - 保存成功時にメッセージを表示
  - _Requirements: 6.2, 6.3, 6.4_

- [ ] 11. 統合テストと E2E テスト
- [ ] 11.1 バックエンド統合テストを追加
  - 認証 → 一覧取得 → is_ready 更新のフローテスト
  - annotator が is_ready=FALSE の画像にアクセスで 403 確認
  - バッチ更新の複数レコード処理テスト
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.4_

- [ ]*11.2 フロントエンド E2E テストを追加（MVP後対応可）
  - admin ログイン → is_ready トグル操作 → 状態反映確認
  - annotator ログイン → is_ready UI 非表示確認
  - is_ready フィルターによる一覧絞り込み確認
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4_

---

## Requirements Coverage

| Requirement | Tasks |
|-------------|-------|
| 1.1 | 1.2, 2.2, 6.1 |
| 1.2 | 4.5 |
| 1.3 | 1.2, 2.2 |
| 2.1 | 1.1, 2.1, 6.1 |
| 2.2 | 2.1, 7.1 |
| 2.3 | 1.1 |
| 2.4 | 2.1, 3.1, 6.1, 6.2 |
| 3.1 | 4.3, 5.3, 6.4, 11.1 |
| 3.2 | 4.3, 5.3, 6.4, 11.1 |
| 3.3 | 4.3, 5.3, 6.4, 11.1 |
| 3.4 | 4.4, 5.4, 6.4, 11.1 |
| 4.1 | 4.1, 5.1, 6.3, 7.2, 11.1 |
| 4.2 | 3.2, 5.1, 6.2, 11.1 |
| 4.3 | 4.1, 5.1, 6.3 |
| 4.4 | 4.2, 5.2, 6.3, 7.2, 11.1 |
| 5.1 | 7.1, 9.1, 11.2 |
| 5.2 | 9.2, 11.2 |
| 5.3 | 9.3, 11.2 |
| 5.4 | 9.1, 9.2, 11.2 |
| 5.5 | 9.3, 11.2 |
| 6.1 | 10.1, 11.2 |
| 6.2 | 10.2, 11.2 |
| 6.3 | 10.1, 10.2, 11.2 |
| 6.4 | 10.2, 11.2 |
| 7.1 | 4.3, 5.3, 6.4, 7.1, 9.4 |
| 7.2 | 4.3, 5.3, 6.4, 9.4 |
| 7.3 | 9.4 |
| 8.1 | 3.1, 3.3, 6.2 |
| 8.2 | 3.1, 3.3, 6.2 |
| 8.3 | 8.1 |

# Implementation Plan

- [x] 1. データベーススキーマ変更とモデル拡張
- [x] 1.1 Treeモデルにversionカラムを追加する
  - treesテーブルにINTEGER型のversionカラムを追加するAlembicマイグレーションを作成する
  - 既存レコードには`202501`をデフォルト値として設定する
  - NOT NULL制約とインデックスを付与する
  - TreeモデルのSQLAlchemy定義にversionフィールドを追加する（デフォルト202501、server_default、index=True）
  - _Requirements: 1.1, 1.2_

- [x] 1.2 (P) 新規Tree作成時のversion設定を確認する
  - 新規Tree作成処理で`version=202601`が設定されるようにする
  - 既存のTree作成ロジックを調査し、適切な箇所でversion値を指定する
  - _Requirements: 1.3_

- [x] 2. アノテーション一覧APIの拡張
- [x] 2.1 レスポンススキーマにversionフィールドを追加する
  - 一覧レスポンスの各アイテムにTreeのversion値を含める
  - _Requirements: 2.1_

- [x] 2.2 versionsクエリパラメータによるフィルタ機能を実装する
  - 一覧取得エンドポイントにversionsクエリパラメータを追加する（カンマ区切り文字列、Optional）
  - カンマ区切り文字列をint型リストに変換するパース処理を実装する（既存のbloom_statusと同パターン）
  - version IN条件をクエリのフィルタチェーンに追加する
  - versionsが未指定の場合はフィルタなし（全件表示）とする
  - 2025年度のみ、2026年度のみ、両方選択、未選択の全パターンに対応する
  - _Requirements: 2.2, 2.3, 2.4, 2.5_

- [x] 2.3 Admin限定のmodel_vitalityフィルタを実装する
  - 一覧取得エンドポイントにmodel_vitalityクエリパラメータを追加する（Optional[int]、Admin限定）
  - EntireTree.vitalityによるフィルタ条件を追加する（既存のvitality_valueフィルタとは別）
  - 非Adminユーザーの場合はmodel_vitalityパラメータを無視する
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 3. アノテーション詳細APIの拡張
- [ ] 3.1 (P) 開花段階日をレスポンスに追加する
  - 詳細レスポンススキーマにbloom_30_date（3分咲き日）とbloom_50_date（5分咲き日）フィールドを追加する（Optional[str]）
  - EntireTreeから直接bloom_30_dateとbloom_50_dateを取得してレスポンスに含める
  - 未記録の場合はnullとして返却する
  - _Requirements: 3.1, 3.2_

- [ ] 3.2 Admin限定の診断値表示を実装する
  - 診断値レスポンス用のサブモデル（DiagnosticsResponse）を定義する
  - vitality、vitality_noleaf、vitality_noleaf_weight、vitality_bloom、vitality_bloom_weight、vitality_bloom_30、vitality_bloom_30_weight、vitality_bloom_50、vitality_bloom_50_weightの9項目を含める
  - 詳細取得処理にAnnotatorオブジェクトを渡し、ロール判定を行う
  - Adminの場合はEntireTreeから診断値を取得してレスポンスに含め、非Adminの場合はnullとする
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 3.3 Admin限定のデバッグ画像URL表示を実装する
  - デバッグ画像レスポンス用のサブモデル（DebugImagesResponse）を定義する（noleaf_url、bloom_url）
  - EntireTreeのdebug_image_obj_keyとdebug_image_obj2_keyからImageServiceでURLを生成する
  - 画像キーがnullの場合は該当URLをnullとする
  - Adminの場合のみデバッグ画像情報を含め、非Adminの場合はnullとする
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 4. 統合とエンドポイント調整
- [ ] 4.1 ルーターのパラメータとレスポンス構築を統合する
  - 一覧エンドポイントでversionsパラメータのパース結果とmodel_vitalityをアプリケーション層に渡す
  - 詳細エンドポイントでAnnotatorオブジェクトをアプリケーション層に渡す
  - 一覧レスポンスにversion値を含めるマッピング処理を追加する
  - 詳細レスポンスにbloom日、diagnostics、debug_imagesを含めるマッピング処理を追加する
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 6.4_

- [ ]* 5. テスト
- [ ]* 5.1 (P) versionフィルタのテストを作成する
  - versionsパラメータのパース処理の正常系・異常系をテストする
  - version IN条件によるフィルタリング結果を検証する
  - 未指定時の全件表示を確認する
  - _Requirements: 2.2, 2.3, 2.4, 2.5_

- [ ]* 5.2 (P) Admin限定機能のテストを作成する
  - Admin時にdiagnostics・debug_imagesが含まれることを検証する
  - 非Admin時にdiagnostics・debug_imagesがnullであることを検証する
  - model_vitalityフィルタのAdmin限定動作を検証する
  - _Requirements: 4.1, 4.2, 5.1, 5.2, 5.3, 6.1, 6.4_

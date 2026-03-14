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

- [x] 3. アノテーション詳細APIの拡張
- [x] 3.1 (P) 開花段階日をレスポンスに追加する
  - 詳細レスポンススキーマにbloom_30_date（3分咲き日）とbloom_50_date（5分咲き日）フィールドを追加する（Optional[str]）
  - EntireTreeから直接bloom_30_dateとbloom_50_dateを取得してレスポンスに含める
  - 未記録の場合はnullとして返却する
  - _Requirements: 3.1, 3.2_

- [x] 3.2 Admin限定の診断値表示を実装する
  - 診断値レスポンス用のサブモデル（DiagnosticsResponse）を定義する
  - vitality、vitality_noleaf、vitality_noleaf_weight、vitality_bloom、vitality_bloom_weight、vitality_bloom_30、vitality_bloom_30_weight、vitality_bloom_50、vitality_bloom_50_weightの9項目を含める
  - 詳細取得処理にAnnotatorオブジェクトを渡し、ロール判定を行う
  - Adminの場合はEntireTreeから診断値を取得してレスポンスに含め、非Adminの場合はnullとする
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 3.3 Admin限定のデバッグ画像URL表示を実装する
  - デバッグ画像レスポンス用のサブモデル（DebugImagesResponse）を定義する（noleaf_url、bloom_url）
  - EntireTreeのdebug_image_obj_keyとdebug_image_obj2_keyからImageServiceでURLを生成する
  - 画像キーがnullの場合は該当URLをnullとする
  - Adminの場合のみデバッグ画像情報を含め、非Adminの場合はnullとする
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 4. 統合とエンドポイント調整
- [x] 4.1 ルーターのパラメータとレスポンス構築を統合する
  - 一覧エンドポイントでversionsパラメータのパース結果とmodel_vitalityをアプリケーション層に渡す
  - 詳細エンドポイントでAnnotatorオブジェクトをアプリケーション層に渡す
  - 一覧レスポンスにversion値を含めるマッピング処理を追加する
  - 詳細レスポンスにbloom日、diagnostics、debug_imagesを含めるマッピング処理を追加する
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 6.4_

- [x] 5. テスト
- [x] 5.1 (P) versionフィルタのテストを作成する
  - versionsパラメータのパース処理の正常系・異常系をテストする
  - version IN条件によるフィルタリング結果を検証する
  - 未指定時の全件表示を確認する
  - _Requirements: 2.2, 2.3, 2.4, 2.5_

- [x] 5.2 (P) Admin限定機能のテストを作成する
  - Admin時にdiagnostics・debug_imagesが含まれることを検証する
  - 非Admin時にdiagnostics・debug_imagesがnullであることを検証する
  - model_vitalityフィルタのAdmin限定動作を検証する
  - _Requirements: 4.1, 4.2, 5.1, 5.2, 5.3, 6.1, 6.4_

- [x] 6. フロントエンド型定義・APIクライアント拡張
- [x] 6.1 TypeScript型定義を拡張する
  - `AnnotationListItem`に`version: number`フィールドを追加する
  - `AnnotationDetail`に`bloom_30_date`、`bloom_50_date`、`diagnostics`、`debug_images`フィールドを追加する
  - `Diagnostics`インターフェースを新規定義する（vitality系9項目）
  - `DebugImages`インターフェースを新規定義する（noleaf_url、bloom_url）
  - `ListFilter`に`versions: string | null`と`model_vitality: number | null`を追加する
  - _Requirements: 全要件_

- [x] 6.2 APIクライアントにversions・model_vitalityパラメータ送信を追加する
  - `getTrees`で`versions`パラメータをカンマ区切り文字列として送信する
  - `getTrees`で`model_vitality`パラメータを送信する
  - `getTreeDetail`で`versions`・`model_vitality`パラメータをナビゲーション維持用に送信する
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 5.1, 5.2_

- [ ] 7. 一覧画面（ListPage）の拡張
- [ ] 7.1 年度チェックボックスフィルタを追加する
  - フィルタセクションに「2025年度」「2026年度」のチェックボックスを追加する
  - 複数選択可能とし、選択状態をURLパラメータ`versions`にカンマ区切りで保持する
  - チェック変更時にページを1にリセットする
  - 未選択時はversionsパラメータを送信しない（全件表示）
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 7.2 Admin限定のmodel_vitalityフィルタを追加する
  - `isAdmin`時のみ表示されるドロップダウンフィルタを追加する（ラベル: 「推論モデル元気度」）
  - 選択肢: 全て、1-5の元気度値
  - URLパラメータ`model_vitality`で状態を管理する
  - 非Admin時はUI非表示かつパラメータ送信なし
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 7.3 カードにバージョンバッジを表示する
  - 各カードにバージョンバッジ（2025年度 / 2026年度）を表示する
  - 2025年度: `bg-blue-100 text-blue-700`、2026年度: `bg-emerald-100 text-emerald-700`
  - _Requirements: 2.1_

- [ ] 8. 詳細画面（AnnotationPage）の拡張
- [ ] 8.1 開花段階日（bloom_30_date/bloom_50_date）を表示する
  - 撮影情報カードの開花日と満開開始日の間に3分咲き日・5分咲き日を追加する
  - `formatDateShort`（M/D形式）で表示する
  - 未記録の場合は`-`を表示する
  - 全ロール共通で表示する
  - _Requirements: 3.1, 3.2_

- [ ] 8.2 Admin限定の診断値セクションを追加する
  - 撮影情報カードの下に「診断値（推論モデル）」カードを追加する
  - vitality系9項目をキー・バリュー形式で表示する
  - weight値は小数点2桁で表示し、nullの場合は`-`を表示する
  - `isAdmin && detail.diagnostics`で条件レンダリングする
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 8.3 Admin限定のデバッグ画像リンクを追加する
  - 診断値セクションの下に「デバッグ画像」カードを追加する
  - `noleaf_url`/`bloom_url`が存在する場合は別タブで開くリンクを表示する（`target="_blank"`）
  - 画像キーがnullの場合は「画像なし」テキストを表示する
  - `isAdmin && detail.debug_images`で条件レンダリングする
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 8.4 詳細画面のナビゲーションにversions・model_vitalityを引き継ぐ
  - `fetchDetail`のフィルタパラメータにversions・model_vitalityを追加する
  - `navigateTo`・`getBackUrl`・`handleItemClick`でversions・model_vitalityパラメータを引き継ぐ
  - _Requirements: 2.2, 5.1_

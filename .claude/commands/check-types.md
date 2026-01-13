# /check-types

Python型注釈の品質チェックを実行し、未注釈の箇所を報告・修正提案する

## 説明
このコマンドは、Pythonコードの型注釈品質を総合的にチェックし、プロジェクトの型安全性を向上させます。CLAUDE.mdで定義された型注釈標準に準拠しているかを確認します。

## 動作
1. **basedpyrightによる型エラーチェック**: 型エラーと未注釈箇所を特定
2. **型注釈カバレッジ分析**: クラス、メソッド、フィールドの注釈状況を確認
3. **`Any`型の使用チェック**: 禁止されている`Any`型の使用を検出
4. **循環インポート問題の検出**: `TYPE_CHECKING`の適切な使用を確認
5. **修正提案**: 検出した問題に対する具体的な修正提案を提示
6. **自動修正**: ユーザー確認後に修正を実行

## 実行対象
- `src/`ディレクトリ下の全Pythonファイル
- 特定ファイルの指定も可能: `/check-types path/to/file.py`

## 出力例
```
=== Type Annotation Quality Check ===

❌ src/features/example.py
  - Line 15: Method 'process' missing return type annotation
  - Line 23: Field 'data' missing type annotation  
  - Line 30: Using 'Any' type (forbidden)

✅ src/features/good_example.py
  - All type annotations present and valid

=== Summary ===
Files checked: 25
Issues found: 3
Type coverage: 92%

=== Suggested Fixes ===
1. Add return type to process() method: -> Optional[Dict[str, str]]
2. Add field annotation: data: List[Any] = []
3. Replace Any with specific type: Union[str, int, bool]

Apply fixes? [y/N]
```

## 設定
- `pyproject.toml`の`[tool.basedpyright]`設定を使用
- 型チェックの厳格度は`strict`モードを適用
- プロジェクト固有の型チェック除外設定に従う

## 関連
- CLAUDE.md「Code Quality Standards」に準拠
- 実装前後での型チェック必須化
- CIパイプラインでの型チェック自動化
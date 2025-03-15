# README

## 起動方法

### 1. 環境変数の設定

`.env`ファイルを作成し、以下の内容を設定してください：

```bash
DB_USER=root
DB_PASSWORD=root
DB_HOST=localhost
DB_NAME=harekaze_db

# JWT設定
# 本番環境では secrets.token_hex(32) で生成した値を使用してください
JWT_SECRET_KEY=8d5f8db058e9297b0048e56b8280dc51f83aa1851b2f4c6b6b8c8c4b6f7c8b1a
```

### 2. 依存関係のインストール

```bash
uv sync
```

### 3. データベースのセットアップ
MySQLサーバーを起動し、データベースを作成してください：

```bash
mysql -u root -p
```

MySQLプロンプトで以下を実行：
```sql
CREATE DATABASE harekaze_db;
```

マイグレーションを実行：
```bash
alembic upgrade head
```

### 4. サーバーの起動

開発サーバーを起動：
```bash
gunicorn main:app --worker-class uvicorn.workers.UvicornWorker --reload --bind 0.0.0.0:8000
```

サーバーが起動したら、以下のURLでSwagger UIにアクセスできます：
http://localhost:8000/docs

## 作業環境セットアップ


```bash
HOMEBREW_NO_AUTO_UPDATE=1 brew install pkg-config
HOMEBREW_NO_AUTO_UPDATE=1 brew install mysql-client
uv init -p 3.12
```

### Ubuntu

```bash
sudo apt update
sudo apt-get install clang
sudo apt install mysql-server-8.0 mysql-client
sudo service mysql start
sudo apt-get install pkg-config libmysqlclient-dev

uv sync
```

## DB操作

### DBリセット、マイグレーション再作成＆実行

```bash
rm -rf migrations/versions/*
# DBリセットも行う
# alembic init migrations
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 一つ前のマイグレーションに戻す

```bash
alembic downgrade -1
```

### 最初の状態に戻す

```bash
alembic downgrade base
```


## Server 公開


https://harekaze-kkcraft.jp.ngrok.io/docs
ID: harekaze
PASS: harekaze2025

```bash
ngrok http --region=ap --basic-auth "harekaze:harekaze2025"--domain=harekaze-kkcraft.jp.ngrok.io 8000
```

## テスト

### テスト環境のセットアップ

テストと開発用の依存関係をインストールします：

```bash
uv pip sync --group test --group dev
```

### テストの実行

全てのテストを実行：

```bash
pytest
```

特定のマーカーのテストのみ実行：

```bash
# 単体テストのみ実行
pytest -m unit

# APIテストのみ実行
pytest -m api

# 結合テストのみ実行
pytest -m integration
```

特定のテストファイルを実行：

```bash
# ファイルを指定して実行
pytest tests/domain/services/test_municipality_service.py

# 特定のクラスを実行
pytest tests/domain/services/test_municipality_service.py::TestMunicipalityService

# 特定のテストメソッドを実行
pytest tests/domain/services/test_municipality_service.py::TestMunicipalityService::test_get_prefecture_code

# 詳細な出力で実行
pytest -v tests/domain/services/test_municipality_service.py
```

カバレッジレポートの生成：

```bash
pytest --cov=app --cov-report=html
```

カバレッジレポートは `htmlcov` ディレクトリに生成されます。

### テストの構造

テストは以下の層に分かれています：

- `tests/domain/`: ドメイン層のテスト
  - ビジネスロジックの単体テスト
  - 外部依存のないピュアな関数のテスト

- `tests/infrastructure/`: インフラストラクチャ層のテスト
  - 外部サービスとのインテグレーション
  - データベース操作のテスト

- `tests/application/`: アプリケーション層のテスト
  - ユースケースのテスト
  - 複数のサービスを組み合わせた統合テスト

- `tests/interfaces/`: インターフェース層のテスト
  - APIエンドポイントのテスト
  - リクエスト/レスポンスの検証


## 樹齢計算式

```bash
python -m app.domain.models.tree_age_plot
```



## 木の登録処理時間内訳

- 住所情報の取得処理: 152.33ms
- 画像の前処理(解析可能な内部形式への変換): 160.35ms
- ラベル検出処理: 1699.53ms
  - Rekognition で画像から人、木の検出
- Lambda が入力とする画像のS3へのアップロード: 548.42ms
  - Lambda に直接渡せないため、S3に一度アップする
- 樹勢モデルによる解析: 6508.20ms
  - Lambda による処理
- 人物ぼかし処理: 833.65ms
- サムネイル作成: 175.78ms
  - 一覧表示用の低解像度の画像を作成
- 画像とサムネイルのS3へのアップロード: 1013.60ms
- DB登録処理: 52.96ms

合計処理時間: 11144.82ms


## 幹の登録処理時間内訳

- 画像の前処理: 560.79ms
- ラベル検出処理: 2029.52ms
  - Rekognition で画像から人、木、缶の検出
- Lambda が入力とする画像のS3へのアップロード: 491.91ms
  - Lambda に直接渡せないため、S3に一度アップする
- 幹モデルによる解析: 11277.53ms
- 人物ぼかし処理: 812.20ms
- サムネイル作成: 310.48ms
- 画像とサムネイルのアップロード: 916.84ms
- DB登録処理: 50.21ms

合計処理時間: 16449.48ms
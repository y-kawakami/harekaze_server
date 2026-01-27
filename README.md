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

```(old)
uvicorn main:app --reload
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

## アノテーションツール

桜画像に対して元気度（1-5、診断不可）をラベル付けするためのWebツールです。
詳細な仕様は `.kiro/specs/sakura-vitality-annotation/requirements.md` を参照してください。

### ローカル開発環境

#### 1. バックエンドAPI起動（ポート8000）

```bash
gunicorn main:app --worker-class uvicorn.workers.UvicornWorker --reload --bind 0.0.0.0:8000
```

#### 2. フロントエンド起動（ポート3000）

```bash
cd frontend/annotation-tool
npm install   # 初回のみ
npm run dev
```

#### 3. アクセス

| 画面 | URL |
|------|-----|
| アノテーションツール | http://localhost:3000 |
| API ドキュメント (Swagger) | http://localhost:8000/docs |

開発モードでは、Viteのプロキシ設定により `/annotation_api` へのリクエストは自動的にバックエンド（ポート8000）に転送されます。

### 本番環境

本番環境ではSPAをビルドし、Webサーバー（nginx等）から静的ファイルとして配信します。

#### 1. SPAビルド

```bash
cd frontend/annotation-tool
npm run build
```

ビルド成果物は `frontend/annotation-tool/dist/` に出力されます。

#### 2. nginx設定例

```nginx
server {
    listen 80;
    server_name annotation.example.com;

    # SPA静的ファイル配信
    location / {
        root /var/www/annotation-tool/dist;
        try_files $uri $uri/ /index.html;
    }

    # APIプロキシ
    location /annotation_api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 認証

アノテーターとしてログインするには、`annotators` テーブルにアカウントが必要です。

#### 初期アカウント

マイグレーション実行時に以下の初期アカウントが作成されます：

| ユーザー名 | パスワード |
|-----------|-----------|
| `annotator` | `annotation2026` |

#### アノテーター管理スクリプト

```bash
# アノテーターを作成
python scripts/create_annotator.py create ユーザー名 パスワード

# アノテーター一覧を表示
python scripts/create_annotator.py list

# アノテーターを削除
python scripts/create_annotator.py delete ユーザー名

# パスワードハッシュのみを生成（DBには登録しない）
python scripts/create_annotator.py create ユーザー名 パスワード --hash-only
```

#### 開花状態更新スクリプト

EntireTree テーブルの bloom_status カラムを一括更新するスクリプトです。
撮影日と撮影場所から8段階の開花状態（開花前、開花、3分咲き、5分咲き、満開、散り始め、花＋若葉、葉のみ）を計算します。

```bash
# ドライランモード（実際の更新を行わず、計算結果のみ表示）
python scripts/update_bloom_status.py --dry-run

# 実行（デフォルトバッチサイズ: 1000）
python scripts/update_bloom_status.py

# バッチサイズを指定して実行
python scripts/update_bloom_status.py --batch-size 500
```

### APIエンドポイント

| Method | Endpoint | 説明 |
|--------|----------|------|
| POST | `/annotation_api/login` | ログイン |
| GET | `/annotation_api/me` | 現在のアノテーター情報取得 |
| GET | `/annotation_api/trees` | 桜画像一覧取得（フィルタリング対応） |
| GET | `/annotation_api/trees/{id}` | 桜画像詳細取得 |
| POST | `/annotation_api/trees/{id}/annotation` | アノテーション保存 |
| GET | `/annotation_api/prefectures` | 都道府県一覧取得 |
| GET | `/annotation_api/export/csv` | CSVエクスポート |

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



## データ合計数

* 元気度
事務局OK: 24172
事務局NG: 935

* 幹(缶あり)
OK	280
NG	86

* 幹(缶なし)
OK	5953
NG	165

* 幹の空洞
OK 299
NG 35

* コブ
OK 73
NG 23

* テングス
OK 75
NG 22

* きのこ
OK 125
NG 24

## データ集計表

| 種別       | OK     | NG  | 合計   |
| ---------- | ------ | --- | ------ |
| 元気度     | 24,172 | 935 | 25,107 |
| 幹(缶あり) | 280    | 86  | 366    |
| 幹(缶なし) | 5,953  | 165 | 6,118  |
| 幹の空洞   | 299    | 35  | 334    |
| コブ       | 73     | 23  | 96     |
| テングス   | 75     | 22  | 97     |
| きのこ     | 125    | 24  | 149    |



## 集計 SQL

### 元気度

SELECT
  DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d') AS '日付(JST)',
  SUM(CASE WHEN et.censorship_status = 1 THEN 1 ELSE 0 END) AS 'OK',
  SUM(CASE WHEN et.censorship_status = 2 THEN 1 ELSE 0 END) AS 'NG',
  SUM(CASE WHEN et.censorship_status IN (1, 2) THEN 1 ELSE 0 END) AS '合計'
FROM entire_trees et
JOIN trees t ON et.tree_id = t.id
GROUP BY DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d')
ORDER BY `日付(JST)`;

### 幹の寄り

SELECT
  DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d') AS '日付(JST)',
  SUM(CASE WHEN s.can_detected = 1 AND s.censorship_status = 1 THEN 1 ELSE 0 END) AS '缶あり_OK',
  SUM(CASE WHEN s.can_detected = 1 AND s.censorship_status = 2 THEN 1 ELSE 0 END) AS '缶あり_NG',
  SUM(CASE WHEN s.can_detected = 1 AND s.censorship_status IN (1, 2) THEN 1 ELSE 0 END) AS '缶あり_合計',
  SUM(CASE WHEN s.can_detected = 0 AND s.censorship_status = 1 THEN 1 ELSE 0 END) AS '缶なし_OK',
  SUM(CASE WHEN s.can_detected = 0 AND s.censorship_status = 2 THEN 1 ELSE 0 END) AS '缶なし_NG',
  SUM(CASE WHEN s.can_detected = 0 AND s.censorship_status IN (1, 2) THEN 1 ELSE 0 END) AS '缶なし_合計',
  SUM(CASE WHEN s.censorship_status IN (1, 2) THEN 1 ELSE 0 END) AS '合計'
FROM stems s
JOIN trees t ON s.tree_id = t.id
GROUP BY DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d')
ORDER BY `日付(JST)`;

### 幹の穴

SELECT
  DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d') AS '日付(JST)',
  SUM(CASE WHEN sh.censorship_status = 1 THEN 1 ELSE 0 END) AS 'OK',
  SUM(CASE WHEN sh.censorship_status = 2 THEN 1 ELSE 0 END) AS 'NG',
  SUM(CASE WHEN sh.censorship_status IN (1, 2) THEN 1 ELSE 0 END) AS '合計'
FROM stem_holes sh
JOIN trees t ON sh.tree_id = t.id
GROUP BY DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d')
ORDER BY `日付(JST)`;

### コブ

SELECT
  DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d') AS '日付(JST)',
  SUM(CASE WHEN k.censorship_status = 1 THEN 1 ELSE 0 END) AS 'OK',
  SUM(CASE WHEN k.censorship_status = 2 THEN 1 ELSE 0 END) AS 'NG',
  SUM(CASE WHEN k.censorship_status IN (1, 2) THEN 1 ELSE 0 END) AS '合計'
FROM kobus k
JOIN trees t ON k.tree_id = t.id
GROUP BY DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d')
ORDER BY `日付(JST)`;

### 天狗巣

SELECT
  DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d') AS '日付(JST)',
  SUM(CASE WHEN tg.censorship_status = 1 THEN 1 ELSE 0 END) AS 'OK',
  SUM(CASE WHEN tg.censorship_status = 2 THEN 1 ELSE 0 END) AS 'NG',
  SUM(CASE WHEN tg.censorship_status IN (1, 2) THEN 1 ELSE 0 END) AS '合計'
FROM tengus tg
JOIN trees t ON tg.tree_id = t.id
GROUP BY DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d')
ORDER BY `日付(JST)`;

### キノコ

SELECT
  DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d') AS '日付(JST)',
  SUM(CASE WHEN m.censorship_status = 1 THEN 1 ELSE 0 END) AS 'OK',
  SUM(CASE WHEN m.censorship_status = 2 THEN 1 ELSE 0 END) AS 'NG',
  SUM(CASE WHEN m.censorship_status IN (1, 2) THEN 1 ELSE 0 END) AS '合計'
FROM mushrooms m
JOIN trees t ON m.tree_id = t.id
GROUP BY DATE_FORMAT(DATE_ADD(t.created_at, INTERVAL 9 HOUR), '%Y-%m-%d')
ORDER BY `日付(JST)`;

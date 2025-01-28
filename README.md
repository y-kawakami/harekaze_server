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

## DB操作

### DBリセット、マイグレーション再作成＆実行

```bash
rm -rf migrations/*
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
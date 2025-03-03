#!/bin/bash

# スクリプトが失敗した場合即座に終了
set -e

# 環境変数ファイルの読み込み
if [ ! -f .env.production ]; then
    echo ".env.production ファイルが見つかりません"
    exit 1
fi

source .env.production

# リモートデータベースの設定を一時保存
REMOTE_DB_HOST="${DB_HOST}"

# ローカルホストの設定
export DB_HOST="127.0.0.1"
export DB_PORT="${LOCAL_PORT}"

# SSHトンネルの設定
echo "SSHトンネルを確立しています..."
ssh -f -N -L ${LOCAL_PORT}:${REMOTE_DB_HOST}:3306 \
    -i ${SSH_KEY_PATH} \
    ${SSH_USER}@${BASTION_HOST} \
    -o ExitOnForwardFailure=yes

# トンネルが確立されるまで少し待機
sleep 2

# 終了時の処理を関数化
cleanup() {
    echo "SSHトンネルを終了しています..."
    # プロセスIDを取得して終了
    local tunnel_pid=$(ps aux | grep "ssh -f -N -L ${LOCAL_PORT}:${REMOTE_DB_HOST}:3306" | grep -v grep | awk '{print $2}')
    echo "tunnel_pid: $tunnel_pid"
    if [ -n "$tunnel_pid" ]; then
        kill $tunnel_pid || true
    fi
}

# スクリプト終了時に必ずcleanupを実行
trap cleanup EXIT

# SSHトンネルの状態確認
echo "SSHトンネルの状態確認:"
netstat -an | grep ${LOCAL_PORT}

# MySQLへの接続テスト（詳細なデバッグ情報を表示）
echo "接続情報:"
echo "Remote Host: ${REMOTE_DB_HOST}"
echo "Local Host: ${DB_HOST}"
echo "Local Port: ${DB_PORT}"
echo "User: ${DB_USER}"
echo "Database: ${DB_NAME}"

# データベース接続文字列の設定
# export SQLALCHEMY_DATABASE_URL="mysql+mysqlconnector://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# マイグレーションの実行
echo "マイグレーションを実行しています..."
if ! alembic upgrade head; then
    echo "マイグレーションに失敗しました"
    exit 1
fi
echo "マイグレーションが完了しました"

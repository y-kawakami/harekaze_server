#!/bin/bash

# CloudWatch Logs tail スクリプト
# Usage: ./scripts/tail_logs.sh [dev|prd|both]

set -euo pipefail

export AWS_PROFILE=hrkz_cdk
export AWS_REGION=ap-northeast-1

ENV="${1:-dev}"

LOG_GROUP_DEV="/aws/ecs/hrkz-dev-app"
LOG_GROUP_PRD="/aws/ecs/hrkz-prd-app"

tail_log() {
  local log_group="$1"
  local label="$2"
  echo "📡 ${label} ログを tail 中: ${log_group}"
  aws logs tail "$log_group" --follow --since 5m --format short
}

case "$ENV" in
  dev)
    tail_log "$LOG_GROUP_DEV" "dev"
    ;;
  prd)
    tail_log "$LOG_GROUP_PRD" "prd"
    ;;
  both)
    echo "両環境のログを同時に tail します (Ctrl+C で停止)"
    echo ""

    cleanup() {
      echo ""
      echo "ログ tail を停止します..."
      kill 0 2>/dev/null
      wait 2>/dev/null
    }
    trap cleanup EXIT INT TERM

    tail_log "$LOG_GROUP_DEV" "dev" &
    tail_log "$LOG_GROUP_PRD" "prd" &
    wait
    ;;
  *)
    echo "Usage: $0 [dev|prd|both]"
    echo "  dev  : 開発環境 (default)"
    echo "  prd  : 本番環境"
    echo "  both : 両環境を同時に tail"
    exit 1
    ;;
esac

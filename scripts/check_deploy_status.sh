#!/bin/bash

set -euo pipefail

# === 引数パース ===
WATCH=false
while getopts "w" opt; do
    case $opt in
        w) WATCH=true ;;
        *) ;;
    esac
done
shift $((OPTIND - 1))

# === 引数バリデーション ===
if [ $# -ne 2 ]; then
    echo "Usage: $0 [-w] <dev|prd> <app-api|admin-api|annotation-api>"
    echo ""
    echo "Options:"
    echo "  -w    デプロイ完了までポーリング (10秒間隔)"
    echo ""
    echo "Examples:"
    echo "  $0 dev app-api"
    echo "  $0 -w prd admin-api"
    exit 1
fi

ENV=$1
SERVICE=$2

if [ "$ENV" != "dev" ] && [ "$ENV" != "prd" ]; then
    echo "エラー: 環境は dev または prd を指定してください"
    exit 1
fi

if [ "$SERVICE" != "app-api" ] && [ "$SERVICE" != "admin-api" ] && [ "$SERVICE" != "annotation-api" ]; then
    echo "エラー: サービス名は app-api, admin-api, annotation-api のいずれかを指定してください"
    exit 1
fi

# === AWS設定 ===
export AWS_PROFILE=hrkz_cdk
export AWS_REGION=ap-northeast-1

CLUSTER="hrkz-${ENV}-cluster"
ECS_SERVICE="hrkz-${ENV}-${SERVICE}"

# === 状態表示関数 ===
check_status() {
    echo "========================================"
    echo " ECS Deploy Status"
    echo " Cluster: ${CLUSTER}"
    echo " Service: ${ECS_SERVICE}"
    echo " $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    echo ""

    # サービス情報取得
    SERVICE_JSON=$(aws ecs describe-services \
        --cluster "$CLUSTER" \
        --services "$ECS_SERVICE" \
        --query 'services[0]' \
        --output json)

    # --- デプロイメント状態 ---
    echo "--- Deployments ---"
    DEPLOYMENTS=$(echo "$SERVICE_JSON" | jq -r '.deployments')
    DEPLOYMENT_COUNT=$(echo "$DEPLOYMENTS" | jq 'length')

    for i in $(seq 0 $((DEPLOYMENT_COUNT - 1))); do
        DEP=$(echo "$DEPLOYMENTS" | jq ".[$i]")
        STATUS=$(echo "$DEP" | jq -r '.status')
        ROLLOUT=$(echo "$DEP" | jq -r '.rolloutState // "N/A"')
        DESIRED=$(echo "$DEP" | jq -r '.desiredCount')
        RUNNING=$(echo "$DEP" | jq -r '.runningCount')
        PENDING=$(echo "$DEP" | jq -r '.pendingCount')
        TASK_DEF=$(echo "$DEP" | jq -r '.taskDefinition' | awk -F'/' '{print $NF}')
        CREATED=$(echo "$DEP" | jq -r '.createdAt' | cut -d'.' -f1)

        echo "  [$STATUS] rollout=${ROLLOUT}  desired=${DESIRED} running=${RUNNING} pending=${PENDING}"
        echo "    taskDef: ${TASK_DEF}"
        echo "    created: ${CREATED}"
        echo ""
    done

    # --- タスク一覧 ---
    echo "--- Tasks ---"
    TASK_ARNS=$(aws ecs list-tasks \
        --cluster "$CLUSTER" \
        --service-name "$ECS_SERVICE" \
        --query 'taskArns' \
        --output json)

    TASK_COUNT=$(echo "$TASK_ARNS" | jq 'length')

    if [ "$TASK_COUNT" -eq 0 ]; then
        echo "  (タスクなし)"
    else
        TASKS_JSON=$(aws ecs describe-tasks \
            --cluster "$CLUSTER" \
            --tasks $(echo "$TASK_ARNS" | jq -r '.[]') \
            --query 'tasks' \
            --output json)

        for i in $(seq 0 $((TASK_COUNT - 1))); do
            TASK=$(echo "$TASKS_JSON" | jq ".[$i]")
            TASK_ID=$(echo "$TASK" | jq -r '.taskArn' | awk -F'/' '{print $NF}')
            LAST_STATUS=$(echo "$TASK" | jq -r '.lastStatus')
            HEALTH=$(echo "$TASK" | jq -r '.healthStatus // "N/A"')
            TASK_DEF_REV=$(echo "$TASK" | jq -r '.taskDefinitionArn' | awk -F'/' '{print $NF}')
            STARTED=$(echo "$TASK" | jq -r '.startedAt // "N/A"' | cut -d'.' -f1)

            echo "  ${TASK_ID}  status=${LAST_STATUS}  health=${HEALTH}  taskDef=${TASK_DEF_REV}  started=${STARTED}"
        done
    fi
    echo ""

    # --- デプロイ完了判定 ---
    PRIMARY_ONLY=$(echo "$DEPLOYMENTS" | jq '[.[] | select(.status == "PRIMARY")] | length == 1 and length == 1')
    PRIMARY_RUNNING=$(echo "$DEPLOYMENTS" | jq -r '[.[] | select(.status == "PRIMARY")][0].runningCount')
    PRIMARY_DESIRED=$(echo "$DEPLOYMENTS" | jq -r '[.[] | select(.status == "PRIMARY")][0].desiredCount')
    PRIMARY_ROLLOUT=$(echo "$DEPLOYMENTS" | jq -r '[.[] | select(.status == "PRIMARY")][0].rolloutState // "N/A"')

    if [ "$DEPLOYMENT_COUNT" -eq 1 ] && [ "$PRIMARY_RUNNING" -eq "$PRIMARY_DESIRED" ] && [ "$PRIMARY_ROLLOUT" = "COMPLETED" ]; then
        echo "==> デプロイ完了"
        return 0
    else
        echo "==> デプロイ進行中..."
        return 1
    fi
}

# === メイン ===
if [ "$WATCH" = true ]; then
    echo "ポーリングモード: 10秒間隔でデプロイ完了を待機します (Ctrl+C で中断)"
    echo ""
    while true; do
        if check_status; then
            exit 0
        fi
        echo ""
        echo "次の確認まで10秒待機..."
        sleep 10
        clear
    done
else
    check_status
    exit $?
fi

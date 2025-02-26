#!/bin/bash

# サービス名の検証
if [ "$1" != "app-api" ] && [ "$1" != "admin-api" ]; then
    echo "Usage: $0 [app-api|admin-api]"
    echo "サービス名は app-api または admin-api を指定してください"
    exit 1
fi

export AWS_PROFILE=hrkz_cdk
export AWS_ACCOUNT_ID=682033493042
export AWS_REGION=ap-northeast-1
export SERVICE=$1
export IMAGE_TAG=production

$(pwd)/Docker/build-to-ecr.sh

# サービス名に応じてECSサービス名を設定
aws ecs update-service --cluster hrkz-prd-cluster --service hrkz-prd-${SERVICE} --force-new-deployment

#!/bin/bash

export AWS_PROFILE=hrkz_cdk
export AWS_REGION=ap-northeast-1
export S3_BUCKET=hrkz-prd-s3-annotation-front
export CLOUDFRONT_DISTRIBUTION_ID=E37O9JFP7SI2BJ

# フロントエンドディレクトリへ移動
cd "$(dirname "$0")/../frontend/annotation-tool"

# 依存関係インストール
npm ci

# ビルド
npm run build

# S3 へアップロード（既存ファイルで不要なものは削除）
aws s3 sync dist/ s3://${S3_BUCKET}/ --delete

# CloudFront キャッシュ invalidation
aws cloudfront create-invalidation --distribution-id ${CLOUDFRONT_DISTRIBUTION_ID} --paths "/*"

echo "Deploy to prd completed!"

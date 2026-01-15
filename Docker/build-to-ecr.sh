get_image_tag() {
  if [ -e .git-commit-tag ]; then
    cat .git-commit-tag
  elif [ ! -z "$IMAGE_TAG" ]; then
    echo ${IMAGE_TAG}
  else
    echo latest
  fi
}

image_tag=$(get_image_tag)

echo Build started on $(date)
echo Building the Docker image...
echo Image Tag is ${image_tag}

build_app_api=0
build_admin_api=0
build_annotation_api=0
build_manage_api=0
build_data_batch=0

if [ ${SERVICE} = "app-api" ]; then
  build_app_api=1
elif [ ${SERVICE} = "admin-api" ]; then
  build_admin_api=1
elif [ ${SERVICE} = "annotation-api" ]; then
  build_annotation_api=1
elif [ ${SERVICE} = "manage-api" ]; then
  build_manage_api=1
elif [ ${SERVICE} = "data-batch" ]; then
  build_data_batch=1
elif [ ${SERVICE} = "all" ]; then
  build_app_api=1
  build_admin_api=0
  build_annotation_api=0
  build_manage_api=0
  build_data_batch=0
fi

pushed_repositories=""
if [ $build_app_api -eq 1 ]; then
  docker build -t "hrkz-app-api:${image_tag}" -f Docker/Dockerfile.appapi .
  if [ $? -ne 0 ]; then
    echo "build app-api failed"
    exit 1
  fi
  pushed_repositories="${pushed_repositories}app-api "
fi
if [ $build_admin_api -eq 1 ]; then
  docker build -t "hrkz-admin-api:${image_tag}" -f Docker/Dockerfile.adminapi .
  if [ $? -ne 0 ]; then
    echo "build admin-api failed"
    exit 1
  fi
  pushed_repositories="${pushed_repositories}admin-api "
fi
if [ $build_annotation_api -eq 1 ]; then
  echo "build annotation-api"
  docker build -t "hrkz-annotation-api:${image_tag}" -f Docker/Dockerfile.annotationapi .
  if [ $? -ne 0 ]; then
    echo "build annotation-api failed"
    exit 1
  fi
  pushed_repositories="${pushed_repositories}annotation-api "
fi
if [ $build_manage_api -eq 1 ]; then
  docker build -t "hrkz-manage-api:${image_tag}" -f Docker/Dockerfile.manageapi .
  if [ $? -ne 0 ]; then
    echo "build manage-api failed"
    exit 1
  fi
  pushed_repositories="${pushed_repositories}manage-api "
fi
if [ $build_data_batch -eq 1 ]; then
  docker build --platform linux/amd64 -t "hrkz-data-batch:${image_tag}" -f Docker/Dockerfile.batch .
  if [ $? -ne 0 ]; then
    echo "build data-batch failed"
    exit 1
  fi
  pushed_repositories="${pushed_repositories}data-batch "
fi

echo Build completed on $(date)

ECR_REPO_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo Logging in to Amazon ECR...

# for old version
# $(aws ecr get-login --region ${AWS_REGION} --no-include-email)

# for newer version
$(aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin https://$ECR_REPO_URI)

echo Pushing the Docker images...

for repo in $pushed_repositories; do
  echo Pushing image for $repo

  docker tag "hrkz-${repo}:${image_tag}" "${ECR_REPO_URI}/hrkz-${repo}:${image_tag}"
  docker push "${ECR_REPO_URI}/hrkz-${repo}:${image_tag}"
  if [ $? -ne 0 ]; then
    echo "docker push "${ECR_REPO_URI}/hrkz-${repo}:${image_tag}" failed"
    exit 1
  fi

  echo Writing image definitions file for $repo

  # imagedefinitions.json
  cat <<__JSON__ >${repo}_imagedefinitions.json
[
  {"name": "main", "imageUri": "${ECR_REPO_URI}/hrkz-${repo}:${image_tag}"}
]
__JSON__

done

echo build-to-ecr.sh $(date) Done!!!

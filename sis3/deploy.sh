#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <prefix> <env> <sender-email>" >&2
  exit 1
fi

PREFIX="$1"
ENV="$2"
SENDER_EMAIL="$3"

cd "$(dirname "$0")"

if [ -n "$(git status --porcelain -- services/api)" ]; then
  echo "services/api has uncommitted changes, commit them first" >&2
  exit 1
fi

ECR_STACK="${PREFIX}-ecr"
NETWORK_STACK="${PREFIX}-network"
APP_STACK="${PREFIX}"

sam deploy \
  --template-file ecr.yaml \
  --stack-name "$ECR_STACK" \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset

REPOSITORY_URI="$(aws cloudformation describe-stacks \
  --stack-name "$ECR_STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='RepositoryUri'].OutputValue" \
  --output text)"
REGISTRY="${REPOSITORY_URI%%/*}"
REPOSITORY_NAME="${REPOSITORY_URI#*/}"
IMAGE_TAG="$(git rev-parse --short HEAD)"
IMAGE_URI="${REPOSITORY_URI}:${IMAGE_TAG}"

if aws ecr describe-images \
  --repository-name "$REPOSITORY_NAME" \
  --image-ids imageTag="$IMAGE_TAG" >/dev/null 2>&1; then
  echo "Image $IMAGE_URI already exists, skipping build"
else
  aws ecr get-login-password | podman login --username AWS --password-stdin "$REGISTRY"
  podman build --platform linux/amd64 -t "$IMAGE_URI" services/api
  podman push "$IMAGE_URI"
fi

sam deploy \
  --template-file network.yaml \
  --stack-name "$NETWORK_STACK" \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset

sam build

sam deploy \
  --stack-name "$APP_STACK" \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    NetworkStackName="$NETWORK_STACK" \
    ImageUri="$IMAGE_URI" \
    Env="$ENV" \
    SenderEmail="$SENDER_EMAIL"
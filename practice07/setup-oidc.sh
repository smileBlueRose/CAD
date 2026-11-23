#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <github-environment>" >&2
  exit 1
fi

GITHUB_ENVIRONMENT="$1"
STACK_NAME="practice07-github-oidc"

cd "$(dirname "$0")"

REPOSITORY="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
SUBJECT_PREFIX="$(gh api "repos/${REPOSITORY}/actions/oidc/customization/sub" --jq .sub_claim_prefix)"

aws cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --template-file github-oidc.yaml \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    GitHubSubjectPrefix="$SUBJECT_PREFIX" \
    GitHubEnvironment="$GITHUB_ENVIRONMENT"

aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='DeployRoleArn'].OutputValue" \
  --output text
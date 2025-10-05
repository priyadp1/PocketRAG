#!/usr/bin/env bash
set -euo pipefail
REGION="${REGION:-us-east-1}"
SERVICE_NAME="${SERVICE_NAME:-pocketrag-service}"
ECR_REPO="${ECR_REPO:-pocketrag-app}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ROLE_NAME="${ROLE_NAME:-AppRunnerECRAccessRole}"
GENAI_MODEL="${GENAI_MODEL:-gemini-1.5-pro-latest}"
: "${GOOGLE_API_KEY:?Set GOOGLE_API_KEY in your env (export GOOGLE_API_KEY=...)}"
MANAGED_POLICY_ARN="arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG"
if aws ecr describe-repositories --region "$REGION" --repository-names "$ECR_REPO" >/dev/null 2>&1; then
  echo "[ECR] Repo exists"
else
  aws ecr create-repository --region "$REGION" --repository-name "$ECR_REPO" >/dev/null
fi
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
docker build -t "$ECR_REPO:$IMAGE_TAG" .
docker tag "$ECR_REPO:$IMAGE_TAG" "$ECR_URI"
docker push "$ECR_URI"
if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "[IAM] Role exists"
else
  TRUST_DOC="$(mktemp)"
  cat > "$TRUST_DOC" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Principal": { "Service": "build.apprunner.amazonaws.com" }, "Action": "sts:AssumeRole" },
    { "Effect": "Allow", "Principal": { "Service": "tasks.apprunner.amazonaws.com" }, "Action": "sts:AssumeRole" }
  ]
}
JSON
  aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document "file://$TRUST_DOC" >/dev/null
  aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "$MANAGED_POLICY_ARN" >/dev/null
  rm -f "$TRUST_DOC"
fi
ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)"
CREATE_JSON="$(mktemp)"
SRC_JSON="$(mktemp)"
cat > "$CREATE_JSON" <<JSON
{
  "ServiceName": "$SERVICE_NAME",
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "$ECR_URI",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "5050",
        "RuntimeEnvironmentVariables": {
          "GOOGLE_API_KEY": "$GOOGLE_API_KEY",
          "GENAI_MODEL": "$GENAI_MODEL"
        }
      }
    },
    "AuthenticationConfiguration": { "AccessRoleArn": "$ROLE_ARN" }
  }
}
JSON
cat > "$SRC_JSON" <<JSON
{
  "ImageRepository": {
    "ImageIdentifier": "$ECR_URI",
    "ImageRepositoryType": "ECR",
    "ImageConfiguration": {
      "Port": "5050",
      "RuntimeEnvironmentVariables": {
        "GOOGLE_API_KEY": "$GOOGLE_API_KEY",
        "GENAI_MODEL": "$GENAI_MODEL"
      }
    }
  },
  "AuthenticationConfiguration": { "AccessRoleArn": "$ROLE_ARN" }
}
JSON
SERVICE_ARN="$(aws apprunner list-services --region "$REGION" --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn | [0]" --output text)"
if [[ "$SERVICE_ARN" == "None" || -z "$SERVICE_ARN" ]]; then
  SERVICE_ARN="$(aws apprunner create-service --region "$REGION" --cli-input-json "file://$CREATE_JSON" --query 'Service.ServiceArn' --output text)"
else
  aws apprunner update-service --region "$REGION" --service-arn "$SERVICE_ARN" --source-configuration "file://$SRC_JSON" >/dev/null
  aws apprunner start-deployment --service-arn "$SERVICE_ARN" --region "$REGION" >/dev/null
fi
rm -f "$CREATE_JSON" "$SRC_JSON"
for _ in {1..60}; do
  STATUS="$(aws apprunner describe-service --region "$REGION" --service-arn "$SERVICE_ARN" --query 'Service.Status' --output text)"
  URL="$(aws apprunner describe-service --region "$REGION" --service-arn "$SERVICE_ARN" --query 'Service.ServiceUrl' --output text)"
  echo "Status: $STATUS"
  if [[ "$STATUS" == "RUNNING" ]]; then
    echo "Deployed: $URL"
    exit 0
  fi
  sleep 5
done
echo "Timed out waiting for RUNNING"

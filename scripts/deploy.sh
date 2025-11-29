#!/bin/bash
set -e

# Deployment script for Frontier Audio Backend
# Usage: ./scripts/deploy.sh [--skip-build] [--skip-cdk] [--skip-migrate]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPO_NAME="jpwhite-frontier-backend"
ECS_CLUSTER="jpwhite-frontier-cluster"
ECS_SERVICE="jpwhite-frontier-backend"

# Parse arguments
SKIP_BUILD=false
SKIP_CDK=false
SKIP_MIGRATE=false

for arg in "$@"; do
  case $arg in
    --skip-build)
      SKIP_BUILD=true
      ;;
    --skip-cdk)
      SKIP_CDK=true
      ;;
    --skip-migrate)
      SKIP_MIGRATE=true
      ;;
  esac
done

echo "=========================================="
echo "Frontier Audio Backend Deployment"
echo "=========================================="

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "ECR Repository: $ECR_REPO_URI"
echo ""

# Step 1: Build and push Docker image
if [ "$SKIP_BUILD" = false ]; then
  echo "Step 1: Building and pushing Docker image..."

  # Login to ECR
  echo "  - Logging in to ECR..."
  aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO_URI

  # Build image (for linux/amd64 - required for ECS Fargate)
  echo "  - Building Docker image for linux/amd64..."
  docker build --platform linux/amd64 -t $ECR_REPO_NAME "$PROJECT_ROOT/backend"

  # Tag image
  echo "  - Tagging image..."
  docker tag $ECR_REPO_NAME:latest $ECR_REPO_URI:latest

  # Push image
  echo "  - Pushing image to ECR..."
  docker push $ECR_REPO_URI:latest

  echo "  - Docker image pushed successfully!"
else
  echo "Step 1: Skipping Docker build (--skip-build)"
fi
echo ""

# Step 2: Deploy CDK infrastructure
if [ "$SKIP_CDK" = false ]; then
  echo "Step 2: Deploying CDK infrastructure..."
  cd "$PROJECT_ROOT/infra"

  # Load .env file if it exists
  if [ -f .env ]; then
    set -a
    source .env
    set +a
  fi

  npx cdk deploy --require-approval never

  echo "  - CDK deployment complete!"
  cd "$PROJECT_ROOT"
else
  echo "Step 2: Skipping CDK deploy (--skip-cdk)"
fi
echo ""

# Step 3: Run database migrations
if [ "$SKIP_MIGRATE" = false ]; then
  echo "Step 3: Running database migrations..."
  echo "  - Note: Run migrations manually or use: ./scripts/migrate.sh"
  echo "  - Skipping automatic migration (requires DB access)"
else
  echo "Step 3: Skipping migrations (--skip-migrate)"
fi
echo ""

# Step 4: Force new ECS deployment
echo "Step 4: Forcing new ECS deployment..."
aws ecs update-service \
  --cluster $ECS_CLUSTER \
  --service $ECS_SERVICE \
  --force-new-deployment \
  --region $AWS_REGION \
  --query 'service.serviceName' \
  --output text

echo "  - ECS deployment triggered!"
echo ""

# Step 5: Wait for deployment (optional)
echo "Step 5: Waiting for service to stabilize..."
echo "  - This may take a few minutes..."
aws ecs wait services-stable \
  --cluster $ECS_CLUSTER \
  --services $ECS_SERVICE \
  --region $AWS_REGION

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "API URL: https://jpwhite.gauntlet3.com"
echo ""
echo "To check service status:"
echo "  aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION"
echo ""
echo "To view logs:"
echo "  aws logs tail /ecs/jpwhite-frontier-backend --follow --region $AWS_REGION"

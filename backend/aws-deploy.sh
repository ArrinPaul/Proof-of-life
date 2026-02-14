#!/bin/bash

# AWS Deployment Script for Proof-of-Life Backend
# Prerequisites: AWS CLI configured, Docker installed

# Configuration
AWS_REGION="us-east-1"
ECR_REPO_NAME="proof-of-life-backend"
ECS_CLUSTER_NAME="proof-of-life-cluster"
ECS_SERVICE_NAME="proof-of-life-service"
TASK_FAMILY="proof-of-life-task"

echo "Starting AWS deployment..."

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "ECR URI: $ECR_URI"

# Create ECR repository if it doesn't exist
echo "Creating ECR repository..."
aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION 2>/dev/null || echo "Repository already exists"

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

# Build Docker image
echo "Building Docker image..."
docker build -t $ECR_REPO_NAME:latest .

# Tag image
echo "Tagging image..."
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest

# Push to ECR
echo "Pushing image to ECR..."
docker push $ECR_URI:latest

echo "Deployment complete!"
echo "ECR Image: $ECR_URI:latest"
echo ""
echo "Next steps:"
echo "1. Create ECS cluster: aws ecs create-cluster --cluster-name $ECS_CLUSTER_NAME"
echo "2. Create task definition with the image: $ECR_URI:latest"
echo "3. Create ECS service"
echo "4. Configure Application Load Balancer"
echo "5. Update environment variables in task definition"

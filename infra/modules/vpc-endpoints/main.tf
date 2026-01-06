########################################
# 🔌 VPC ENDPOINTS MODULE
########################################
# This module creates VPC endpoints for ECR, S3, and STS
# to eliminate internet dependency and fix ECR timeout issues

variable "vpc_id" {
  description = "VPC ID where endpoints will be created"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for interface endpoints (where ECS tasks run)"
  type        = list(string)
}

variable "aws_region" {
  description = "AWS region for service endpoints"
  type        = string
}

variable "ecs_sg_id" {
  description = "Security group ID of ECS tasks (to allow access to endpoints)"
  type        = string
}

variable "route_table_ids" {
  description = "Route table IDs for S3 gateway endpoint (optional - will auto-discover if empty)"
  type        = list(string)
  default     = []
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
}


########################################
# 🔍 AUTO-DISCOVER ALL ROUTE TABLES IN VPC
########################################
# This ensures S3 gateway endpoint works for ALL subnets
# regardless of which route table they use

data "aws_route_tables" "vpc_route_tables" {
  vpc_id = var.vpc_id
}


########################################
#  ECR API INTERFACE ENDPOINT
########################################
# Endpoint for ECR API calls (GetAuthorizationToken, etc.)

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.subnet_ids
  security_group_ids  = [var.ecs_sg_id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-ecr-api-endpoint"
    Environment = var.environment
  }
}


########################################
# 🐳 ECR DOCKER REGISTRY ENDPOINT
########################################
# Endpoint for Docker registry operations (docker pull)

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.subnet_ids
  security_group_ids  = [var.ecs_sg_id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-ecr-dkr-endpoint"
    Environment = var.environment
  }
}


########################################
# 🔑 STS INTERFACE ENDPOINT
########################################
# Endpoint for AWS Security Token Service (for IAM role assumptions)

resource "aws_vpc_endpoint" "sts" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.sts"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.subnet_ids
  security_group_ids  = [var.ecs_sg_id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-sts-endpoint"
    Environment = var.environment
  }
}


########################################
# 🪣 S3 GATEWAY ENDPOINT
########################################
# Gateway endpoint for S3 (ECR stores image layers in S3)
# No security group needed for gateway endpoints
# CRITICAL: Must be associated with ALL route tables in VPC

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  
  # Use ALL route tables in VPC to ensure all subnets can access S3 privately
  # This prevents tasks from hitting public S3 IPs and timing out
  route_table_ids   = length(var.route_table_ids) > 0 ? var.route_table_ids : data.aws_route_tables.vpc_route_tables.ids

  tags = {
    Name        = "${var.project_name}-${var.environment}-s3-endpoint"
    Environment = var.environment
  }
}


########################################
# 📊 CLOUDWATCH LOGS ENDPOINT (Optional but recommended)
########################################
# Endpoint for CloudWatch Logs (reduces latency for log shipping)

resource "aws_vpc_endpoint" "logs" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.subnet_ids
  security_group_ids  = [var.ecs_sg_id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-logs-endpoint"
    Environment = var.environment
  }
}


########################################
# 🔧 SSM INTERFACE ENDPOINT (For ECS Exec)
########################################
# Required for AWS Systems Manager Session Manager
# Enables ECS Exec to establish shell sessions

resource "aws_vpc_endpoint" "ssm" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.ssm"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.subnet_ids
  security_group_ids  = [var.ecs_sg_id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-ssm-endpoint"
    Environment = var.environment
  }
}


########################################
# 💬 SSM MESSAGES ENDPOINT (For ECS Exec)
########################################
# Required for session data channel communication
# Must be present for ECS Exec to work

resource "aws_vpc_endpoint" "ssmmessages" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.ssmmessages"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.subnet_ids
  security_group_ids  = [var.ecs_sg_id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-ssmmessages-endpoint"
    Environment = var.environment
  }
}


########################################
# 📡 EC2 MESSAGES ENDPOINT (For ECS Exec)
########################################
# Required for command execution channel
# Completes the trio needed for ECS Exec

resource "aws_vpc_endpoint" "ec2messages" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.ec2messages"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.subnet_ids
  security_group_ids  = [var.ecs_sg_id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-ec2messages-endpoint"
    Environment = var.environment
  }
}


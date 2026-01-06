



#########################################
# 🔹 Global AWS Data Sources (for root)
#########################################

# These data sources let Terraform fetch information 
# about your currently authenticated AWS account and region.
# Useful for dynamic references like ECR repo URLs or tagging.

data "aws_caller_identity" "current" {}
# → Returns info about the AWS account you're authenticated as
# Example: account_id, arn, user_id

data "aws_region" "current" {}
# → Returns info about the AWS region currently in use
# Example: name = "us-east-1"

#########################################
# 🔹 Local Variables
#########################################

locals {
  name_prefix = "niura-staging"
}



#########################################
# 🔹 Network Module (VPC + Subnets)
#########################################

# Creates a dedicated Virtual Private Cloud (VPC) for the staging environment.
# Also sets up subnets, routing, and related networking resources.
# Think of this as your isolated "network space" in AWS.

module "network" {
  source       = "./modules/network"
  project_name = "niura"   # Used for naming AWS resources
  environment  = "staging" # Used to differentiate between dev/staging/prod
}


#########################################
# 🔹 VPC Endpoints Module
#########################################

# Creates VPC endpoints for ECR, S3, STS, and CloudWatch Logs
# This eliminates internet dependency and fixes ECR timeout issues
# by allowing ECS tasks to access AWS services privately

module "vpc_endpoints" {
  source = "./modules/vpc-endpoints"

  vpc_id       = module.network.vpc_id
  subnet_ids   = module.network.subnet_ids
  aws_region   = data.aws_region.current.name
  ecs_sg_id    = module.ecs.ecs_security_group_id
  project_name = "niura"
  environment  = "staging"

  depends_on = [module.network, module.ecs]
}



#########################################
# 🔹 ECR Module (Elastic Container Registry)
#########################################

# This module sets up private ECR repositories for your services.
# Each service gets its own ECR repo to store Docker images.

module "ecr" {
  source       = "./modules/ecr"
  project_name = "niura"
  environment  = "staging"

  # List all the microservices that need ECR repositories.
  services = [
    "gateway",      # For API Gateway container
    "core-service", # For your backend core logic
    "eeg-service",  # For EEG data processing service
    "eeg-worker",   # For Celery worker
    "ocr-service"   # For OCR service
  ]
}


#########################################
# 🔹 ECS Module (Elastic Container Service)
#########################################

# This module defines your ECS cluster and services.
# ECS runs your Docker containers in AWS (similar to Kubernetes but managed).
# It connects to your VPC, pulls images from ECR, and exposes the containers.

module "ecs" {
  source       = "./modules/ecs"
  project_name = "niura"
  environment  = "staging"

  # Network configuration
  vpc_id             = module.network.vpc_id     # Reuse VPC from network module
  subnet_ids         = module.network.subnet_ids # Attach ECS tasks to these subnets
  security_group_ids = []                        # Optionally add SGs here later

  # 🔹 Define which Docker images to deploy
  # The images come from ECR, using your AWS account and region dynamically.
  service_images = {
    gateway        = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/niura-gateway-staging:latest"
    "core-service" = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/niura-core-service-staging:latest"
    "eeg-service"  = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/niura-eeg-service-staging:latest"
    "ocr-service"  = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/niura-ocr-service-staging:latest"
  }

  # 🔹 Port on which your container listens (e.g. FastAPI = 8000)
  container_port = 8000

  # 🔹 Number of container instances to run for each service
  desired_count = 1

  kafka_bootstrap_brokers = module.kafka.kafka_bootstrap_brokers
  kafka_cluster_arn       = module.kafka.kafka_arn

  gateway_db_endpoint = module.rds_gateway.db_endpoint
  gateway_db_name     = module.rds_gateway.db_name
  gateway_db_password = random_password.rds_master_password.result

  core_db_endpoint = module.rds_core.db_endpoint
  core_db_name     = module.rds_core.db_name
  core_db_password = random_password.rds_master_password.result

  # 🔹 Pass environment variables from tfvars to all services
  ecs_task_env_vars = var.ecs_task_env_vars

  depends_on    = [module.bastion]
  bastion_sg_id = module.bastion.bastion_sg_id
}



#########################################
# 🔹 EEG Backup Module
#########################################

# This module handles backup logic (for example, S3 backup buckets,
# lifecycle policies, etc.) for EEG data or logs.
# The implementation lives in ./modules/eeg_backup

module "eeg_backup" {
  source = "./modules/eeg_backup"
  
  ecs_task_role_id  = module.ecs.ecs_task_role_id
  subnet_ids        = module.network.subnet_ids
  lambda_sg_id      = module.ecs.ecs_security_group_id
  core_db_endpoint  = module.rds_core.db_endpoint
  core_db_name      = module.rds_core.db_name
  core_db_password  = random_password.rds_master_password.result

  depends_on = [module.ecs, module.rds_core]
}



resource "random_password" "rds_master_password" {
  length  = 16
  special = true
  keepers = {
    # Only regenerate if you manually change this
    regenerate_trigger = "v1"
  }
}

output "rds_password" {
  value     = random_password.rds_master_password.result
  sensitive = true
}


module "rds_gateway" {
  source = "./modules/rds"

  name       = "niura-gateway-db"
  db_name    = "gateway_db"
  username   = "postgres"
  password   = random_password.rds_master_password.result
  subnet_ids = module.network.subnet_ids


  vpc_security_group_ids = [module.ecs.ecs_security_group_id]


  publicly_accessible = false
  environment         = "staging"
}

module "rds_core" {
  source = "./modules/rds"

  name                   = "niura-core-db"
  db_name                = "core_db"
  username               = "postgres"
  password               = random_password.rds_master_password.result
  subnet_ids             = module.network.subnet_ids
  vpc_security_group_ids = [module.ecs.ecs_security_group_id]


  publicly_accessible = false
  environment         = "staging"
}


###############################################
# 🔹 Run automatic Postgres DB initialization
###############################################

# Gateway DB check
module "init_gateway_db" {
  source       = "./modules/postgres-init"
  rds_endpoint = module.rds_gateway.db_endpoint
  db_port      = 5432
  db_name      = module.rds_gateway.db_name
  db_user      = "postgres"
  db_password  = random_password.rds_master_password.result

  depends_on = [module.rds_gateway]
}

# Core DB check
module "init_core_db" {
  source       = "./modules/postgres-init"
  rds_endpoint = module.rds_core.db_endpoint
  db_port      = 5432
  db_name      = module.rds_core.db_name
  db_user      = "postgres"
  db_password  = random_password.rds_master_password.result

  depends_on = [module.rds_core]
}


module "kafka" {
  source = "./modules/kafka-serverless"

  project_name = "niura"
  environment  = "staging"

  vpc_id                      = module.network.vpc_id
  subnet_ids                  = module.network.subnet_ids
  ecs_security_group_id       = module.ecs.ecs_security_group_id
  bastion_security_group_id   = module.bastion.bastion_sg_id
}


module "bastion" {
  source     = "./modules/bastion"
  env_prefix = "niura-staging"

  # Use existing VPC & subnets from your network module
  vpc_id    = module.network.vpc_id
  subnet_id = module.network.public_subnets[0]

  ami_id = data.aws_ami.amazon_linux.id
  
  # MSK Serverless cluster ARN for topic creation permissions
  kafka_cluster_arn = module.kafka.kafka_arn
  aws_region        = var.aws_region
}


output "bastion_instance_id" {
  value = module.bastion.bastion_instance_id
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}


# ============================================================================
# REDIS (ElastiCache) - Celery Broker
# ============================================================================
module "redis" {
  source = "./modules/redis"
  
  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.network.vpc_id
  private_subnet_ids    = module.network.subnet_ids
  ecs_security_group_id = module.ecs.ecs_security_group_id
  
  node_type        = "cache.t4g.small"  # 1.37 GB RAM, ~$24/month (2x micro cost, 2.7x memory)
  num_cache_nodes  = 1                   # Single node for staging
  multi_az_enabled = false
}

# ============================================================================
# EEG WORKER (Celery) - Background Processing
# ============================================================================
module "eeg_worker" {
  source = "./modules/eeg-worker"
  
  project_name            = var.project_name
  environment             = var.environment
  aws_region              = data.aws_region.current.name
  ecs_cluster_id          = module.ecs.cluster_id
  ecs_cluster_name        = module.ecs.cluster_name
  ecs_execution_role_arn  = module.ecs.ecs_execution_role_arn
  ecs_task_role_arn       = module.ecs.ecs_task_role_arn
  ecs_security_group_id   = module.ecs.ecs_security_group_id
  private_subnet_ids      = module.network.subnet_ids
  ecr_repository_url      = module.ecr.repository_urls["eeg-worker"]
  redis_url               = module.redis.redis_connection_string
  kafka_bootstrap_servers = module.kafka.kafka_bootstrap_brokers
  
  worker_cpu           = 2048  # 2 vCPU
  worker_memory        = 4096  # 4 GB
  worker_desired_count = 2     # Start with 2 workers
  worker_min_count     = 1
  worker_max_count     = 10
  
  depends_on = [module.redis, module.ecs]
}


# Add these output blocks to the end of your main.tf file
output "load_balancer_url" {
  description = "URL to access your services"
  value       = "http://${module.ecs.alb_dns}"
}

output "gateway_url" {
  description = "Direct URL to access gateway service"
  value       = "http://${module.ecs.alb_dns}/gateway"
}

output "core_service_url" {
  description = "Direct URL to access core service"
  value       = "http://${module.ecs.alb_dns}/core-service"
}

output "eeg_service_url" {
  description = "Direct URL to access EEG service"
  value       = "http://${module.ecs.alb_dns}/eeg-service"
}

output "ocr_service_url" {
  description = "Direct URL to access OCR service"
  value       = "http://${module.ecs.alb_dns}/ocr-service"
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment (staging/production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "ecs_cluster_id" {
  description = "ECS cluster ID"
  type        = string
}

variable "ecs_cluster_name" {
  description = "ECS cluster name"
  type        = string
}

variable "ecs_execution_role_arn" {
  description = "ECS execution role ARN"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ECS task role ARN"
  type        = string
}

variable "ecs_security_group_id" {
  description = "ECS security group ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "ecr_repository_url" {
  description = "ECR repository URL"
  type        = string
}

variable "redis_url" {
  description = "Redis connection URL"
  type        = string
}

variable "kafka_bootstrap_servers" {
  description = "Kafka bootstrap servers"
  type        = string
}

variable "worker_cpu" {
  description = "CPU units for Celery worker (1024 = 1 vCPU)"
  type        = number
  default     = 2048  # 2 vCPUs for FFT processing
}

variable "worker_memory" {
  description = "Memory for Celery worker in MB"
  type        = number
  default     = 4096  # 4GB for FFT processing
}

variable "worker_desired_count" {
  description = "Desired number of worker tasks"
  type        = number
  default     = 2
}

variable "worker_min_count" {
  description = "Minimum number of worker tasks"
  type        = number
  default     = 1
}

variable "worker_max_count" {
  description = "Maximum number of worker tasks"
  type        = number
  default     = 10
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

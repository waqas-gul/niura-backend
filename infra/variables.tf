variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "ap-south-1"
}

variable "aws_profile" {
  description = "AWS profile to use for authentication"
  type        = string
  default     = "default"
}

variable "environment" {
  description = "Deployment environment name (dev, staging, production)"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "niura"
}

variable "kafka_bootstrap_broker" {
  description = "Kafka bootstrap broker endpoint"
  type        = string
}

variable "ecs_task_env_vars" {
  description = "Environment variables for ECS containers"
  type        = map(string)
  default     = {}
}

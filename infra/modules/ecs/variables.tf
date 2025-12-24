variable "project_name" {
  type = string
}
variable "environment" {
  type = string
}
variable "vpc_id" {
  type = string
}
variable "subnet_ids" {
  type = list(string)
}
variable "security_group_ids" {
  type = list(string)
  default = []
}

# Map of service => image (full ECR image URI with tag)
variable "service_images" {
  type = map(string)
}

variable "container_port" {
  type = number
  default = 8000
}

variable "desired_count" {
  type = number
  default = 1
}


variable "gateway_db_endpoint" {
  description = "RDS endpoint for gateway service"
  type        = string
}


variable "gateway_db_name" {
  description = "Database name for gateway service"
  type        = string
}

variable "core_db_endpoint" {
  description = "RDS endpoint for core service"
  type        = string
}


variable "core_db_password" {
  type        = string
  description = "RDS password for the core service"
  sensitive   = true
}


variable "core_db_name" {
  description = "Database name for core service"
  type        = string
}


variable "gateway_db_password" {
  description = "RDS password for gateway service"
  type        = string
  sensitive   = true
}


# Kafka bootstrap brokers (optional)
variable "kafka_bootstrap_brokers" {
  description = "Kafka bootstrap broker connection string for ECS containers"
  type        = string
  default     = ""
}

variable "bastion_sg_id" {
  description = "Security Group ID of the bastion host (for RDS access)"
  type        = string
  default     = null
}

variable "ecs_task_env_vars" {
  description = "Environment variables for ECS containers"
  type        = map(string)
  default     = {}
}

variable "kafka_cluster_arn" {
  description = "ARN of the Kafka cluster for IAM permissions"
  type        = string
  default     = ""
}

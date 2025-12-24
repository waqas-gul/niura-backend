variable "ecs_task_role_id" {
  description = "IAM role ID for ECS tasks to grant S3 access"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "VPC subnet IDs for Lambda"
  type        = list(string)
  default     = []
}

variable "lambda_sg_id" {
  description = "Security group ID for Lambda to access RDS"
  type        = string
  default     = ""
}

variable "core_db_endpoint" {
  description = "RDS core database endpoint"
  type        = string
  default     = ""
}

variable "core_db_name" {
  description = "RDS core database name"
  type        = string
  default     = ""
}

variable "core_db_password" {
  description = "RDS core database password"
  type        = string
  sensitive   = true
  default     = ""
}

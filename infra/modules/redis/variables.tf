variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment (staging/production)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for Redis"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID of ECS services that need Redis access"
  type        = string
}

variable "node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t4g.small"  # 1.37 GB RAM, ~$24/month
  # Micro (512 MB) fills up too quickly with Celery queues
  # For production, use: cache.r7g.large (13.07 GB) or cache.r7g.xlarge (26.32 GB)
}

variable "num_cache_nodes" {
  description = "Number of cache nodes (1 for staging, 2+ for production with failover)"
  type        = number
  default     = 1
}

variable "multi_az_enabled" {
  description = "Enable Multi-AZ for high availability"
  type        = bool
  default     = false
}

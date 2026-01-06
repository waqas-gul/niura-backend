output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = 6379
}

output "redis_connection_string" {
  description = "Redis connection string for Celery"
  value       = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"
}

output "redis_security_group_id" {
  description = "Security group ID for Redis"
  value       = aws_security_group.redis.id
}

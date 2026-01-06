/**
 * ElastiCache Redis Module
 * Provides managed Redis for Celery broker and result backend
 */

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.project_name}-${var.environment}-redis-subnet"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "${var.project_name}-${var.environment}-redis-subnet"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "redis" {
  name        = "${var.project_name}-${var.environment}-redis-sg"
  description = "Security group for Redis ElastiCache"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis port from ECS services"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.ecs_security_group_id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-redis-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Custom parameter group with eviction policy
resource "aws_elasticache_parameter_group" "redis" {
  name   = "${var.project_name}-${var.environment}-redis-params"
  family = "redis7"

  # Eviction policy: Remove least recently used keys when memory is full
  # volatile-lru: evict keys with TTL set, using LRU algorithm
  # This is ideal for Celery task queues with result expiration
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-redis-params"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "${var.project_name}-${var.environment}-redis"
  description                   = "Redis cluster for Celery broker"
  
  engine                        = "redis"
  engine_version                = "7.0"
  node_type                     = var.node_type
  num_cache_clusters            = var.num_cache_nodes
  
  port                          = 6379
  parameter_group_name          = aws_elasticache_parameter_group.redis.name
  subnet_group_name             = aws_elasticache_subnet_group.redis.name
  security_group_ids            = [aws_security_group.redis.id]
  
  automatic_failover_enabled    = var.num_cache_nodes > 1 ? true : false
  multi_az_enabled              = var.num_cache_nodes > 1 ? var.multi_az_enabled : false
  
  at_rest_encryption_enabled    = true
  transit_encryption_enabled    = false
  
  snapshot_retention_limit      = 5
  snapshot_window               = "03:00-05:00"
  maintenance_window            = "sun:05:00-sun:07:00"
  
  auto_minor_version_upgrade    = true
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-redis"
    Environment = var.environment
    Project     = var.project_name
    Service     = "celery-broker"
  }
}

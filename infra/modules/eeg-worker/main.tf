/**
 * EEG Celery Worker ECS Service
 * Handles CPU-intensive FFT processing asynchronously
 */

resource "aws_ecs_task_definition" "eeg_worker" {
  family                   = "${var.project_name}-${var.environment}-eeg-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name      = "eeg-worker"
      image     = "${var.ecr_repository_url}:latest"
      cpu       = var.worker_cpu
      memory    = var.worker_memory
      essential = true

      environment = [
        {
          name  = "REDIS_URL"
          value = var.redis_url
        },
        {
          name  = "KAFKA_BROKER"
          value = var.kafka_bootstrap_servers
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}-${var.environment}/eeg-worker"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "celery -A app.core.celery_app inspect ping || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name        = "${var.project_name}-${var.environment}-eeg-worker"
    Environment = var.environment
    Project     = var.project_name
    Service     = "eeg-worker"
  }
}

resource "aws_cloudwatch_log_group" "eeg_worker" {
  name              = "/ecs/${var.project_name}-${var.environment}/eeg-worker"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-${var.environment}-eeg-worker-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecs_service" "eeg_worker" {
  name            = "${var.project_name}-${var.environment}-eeg-worker"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.eeg_worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  force_new_deployment = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-eeg-worker-service"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Auto Scaling for Celery Workers
resource "aws_appautoscaling_target" "eeg_worker" {
  max_capacity       = var.worker_max_count
  min_capacity       = var.worker_min_count
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.eeg_worker.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Scale up when CPU is high (processing many tasks)
resource "aws_appautoscaling_policy" "eeg_worker_cpu" {
  name               = "${var.project_name}-${var.environment}-eeg-worker-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.eeg_worker.resource_id
  scalable_dimension = aws_appautoscaling_target.eeg_worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.eeg_worker.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Scale based on memory utilization as secondary metric
resource "aws_appautoscaling_policy" "eeg_worker_memory" {
  name               = "${var.project_name}-${var.environment}-eeg-worker-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.eeg_worker.resource_id
  scalable_dimension = aws_appautoscaling_target.eeg_worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.eeg_worker.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 80.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

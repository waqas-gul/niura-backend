#########################################
# 🔹 AWS Data Sources (for ECS module)
#########################################

# These let Terraform dynamically detect the AWS region and account.
# Useful so you don’t hardcode them — Terraform will auto-detect your credentials.

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}



#########################################
# 🔹 Local variables
#########################################

# A short reusable prefix for naming AWS resources.
# Example: niura-staging
locals {
  name_prefix = "${var.project_name}-${var.environment}"
}



#########################################
# 🔹 ECS Cluster
#########################################

# ECS (Elastic Container Service) is where your containers actually run.
# Think of it as your "Docker host" managed by AWS.
resource "aws_ecs_cluster" "this" {
  name = "${local.name_prefix}-cluster"
}

#########################################
# 🔹 Private DNS Namespace (Cloud Map)
#########################################

# Private DNS namespace for service discovery
resource "aws_service_discovery_private_dns_namespace" "ns" {
  name = "${local.name_prefix}.internal"  # e.g. niura-staging.internal
  vpc  = var.vpc_id

  description = "Private DNS namespace for ECS service discovery"
}



#########################################
# 🔹 IAM Role for ECS Task Execution
#########################################

# This role allows ECS tasks (containers) to:
# - Pull images from ECR
# - Write logs to CloudWatch
# - Access certain AWS APIs (if needed later)
resource "aws_iam_role" "task_execution_role" {
  name = "${local.name_prefix}-ecs-task-exec-role"

  # Define who can assume this role — ECS tasks in this case.
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "ecs-tasks.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
}

# Attach the built-in AWS-managed policy that grants ECR + logging access.
resource "aws_iam_role_policy_attachment" "task_exec_ecr" {
  role       = aws_iam_role.task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

#########################################
# 🔹 ECS Task Role (Runtime Permissions)
#########################################

# This role is assumed by containers at runtime (different from execution role)
# Grants permissions to AWS services like Kafka, S3, etc.
resource "aws_iam_role" "ecs_task_role" {
  name = "${local.name_prefix}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "ecs-tasks.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
}

# MSK (Kafka) permissions for containers
resource "aws_iam_role_policy" "ecs_task_msk_policy" {
  count = var.kafka_cluster_arn != "" ? 1 : 0
  name  = "${local.name_prefix}-msk-policy"
  role  = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "kafka-cluster:Connect",
          "kafka-cluster:DescribeCluster"
        ],
        Resource = [var.kafka_cluster_arn]
      },
      {
        Effect   = "Allow",
        Action   = [
          "kafka-cluster:DescribeTopic",
          "kafka-cluster:CreateTopic",
          "kafka-cluster:WriteData",
          "kafka-cluster:ReadData"
        ],
        Resource = [
          "arn:aws:kafka:${data.aws_region.current.name}:*:topic/*/*/*"
        ]
      },
      {
        Effect   = "Allow",
        Action   = [
          "kafka-cluster:AlterGroup",
          "kafka-cluster:DescribeGroup"
        ],
        Resource = [
          "arn:aws:kafka:${data.aws_region.current.name}:*:group/*/*/*"
        ]
      }
    ]
  })
}

#########################################
# 🔹 Service Discovery Services
#########################################

# Service discovery services (one per microservice)
resource "aws_service_discovery_service" "sd" {
  for_each = var.service_images

  name = each.key
  namespace_id = aws_service_discovery_private_dns_namespace.ns.id

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.ns.id
    routing_policy = "MULTIVALUE" # or "WEIGHTED" if needed
    dns_records {
      ttl = 30
      type = "A"
    }
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    service = each.key
    env     = var.environment
  }
}



#########################################
# 🔹 CloudWatch Log Group (for ECS)
#########################################

# Centralized logging for all your ECS containers.
# Each container will stream its logs here.
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 14 # Keep logs for 14 days
}



#########################################
# 🔹 Application Load Balancer (ALB)
#########################################

# The ALB distributes traffic (HTTP/HTTPS) to your ECS containers.
# Here it’s internet-facing (public) and attached to your subnets.
resource "aws_lb" "alb" {
  name               = "${local.name_prefix}-alb"
  load_balancer_type = "application"
  internal           = false               # false = public facing
  subnets            = var.subnet_ids      # Attach to the subnets from network module

  tags = {
    Name    = "${local.name_prefix}-alb"
    Project = var.project_name
  }
}



#########################################
# 🔹 ALB Security Group
#########################################

# This security group controls who can reach your ALB.
# Allows HTTP (port 80) from anywhere.
resource "aws_security_group" "alb_sg" {
  name        = "${local.name_prefix}-alb-sg"
  description = "ALB security group"
  vpc_id      = var.vpc_id

  # Allow incoming HTTP from anywhere (public internet)
  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound traffic (so containers can reach the internet)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}



# === ECS Task Security Group ===
resource "aws_security_group" "ecs_sg" {
  name        = "${local.name_prefix}-ecs-sg"
  description = "Security group for ECS tasks (allows DB access from tasks)"
  vpc_id      = var.vpc_id

  # Outbound traffic - needed for ECR, updates, etc.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-ecs-sg"
  }
}

# === Self-referencing ingress rule for ECS <-> RDS ===
resource "aws_security_group_rule" "ecs_sg_self_ingress" {
  description              = "Allow PostgreSQL access between tasks/RDS in same SG"
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ecs_sg.id
  source_security_group_id = aws_security_group.ecs_sg.id
}


# === Bastion → RDS PostgreSQL ingress rule ===
resource "aws_security_group_rule" "bastion_to_rds" {
  description              = "Allow bastion EC2 (SSM) to reach RDS PostgreSQL"
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ecs_sg.id
  source_security_group_id = var.bastion_sg_id

}

resource "aws_security_group_rule" "ecs_self_internal_comms" {
  description              = "Allow ECS services in same SG to communicate on ports 8000-8002"
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8002
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ecs_sg.id
  source_security_group_id = aws_security_group.ecs_sg.id
}

# === Allow ECS tasks to access VPC endpoints (HTTPS) ===
resource "aws_security_group_rule" "ecs_to_vpc_endpoints" {
  description              = "Allow ECS tasks to reach VPC endpoints via HTTPS"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ecs_sg.id
  source_security_group_id = aws_security_group.ecs_sg.id
}





#########################################
# 🔹 Optional: Attach Extra Security Groups
#########################################

# If you pass extra security groups via variables,
# this block adds them dynamically to the ALB.
resource "aws_security_group_rule" "alb_attach_extra" {
  count = length(var.security_group_ids) > 0 ? length(var.security_group_ids) : 0

  type                      = "ingress"
  security_group_id         = aws_security_group.alb_sg.id
  source_security_group_id  = var.security_group_ids[count.index]
  from_port                 = 0
  to_port                   = 0
  protocol                  = "-1"
}


# Allow ALB -> ECS communication on container port (8000)
resource "aws_security_group_rule" "alb_to_ecs_http" {
  for_each = local.service_ports

  description              = "Allow ALB to reach ECS tasks on port ${each.value}"
  type                     = "ingress"
  from_port                = each.value
  to_port                  = each.value
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ecs_sg.id
  source_security_group_id = aws_security_group.alb_sg.id
}




#########################################
# 🔹 ALB Listener (Port 80)
#########################################

# The listener “listens” for traffic on port 80 (HTTP).
# If no rule matches the request path, it returns 404 by default.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "No service matched"
      status_code  = "404"
    }
  }
}


locals {
  # Base environment variables for each service
  base_service_envs = {
    gateway = [
      {
        name  = "DATABASE_URL"
        value = "postgresql://postgres:${var.gateway_db_password}@${var.gateway_db_endpoint}:5432/${var.gateway_db_name}"
      },
      {
        name  = "JWT_SECRET_KEY"
        value = "Niura-Secret-Key"
      },
      # Service discovery URLs
      {
        name = "CORE_SERVICE_URL"
        value = "http://core-service.${local.name_prefix}.internal:8001"
      },
      {
        name = "EEG_SERVICE_URL"
        value = "http://eeg-service.${local.name_prefix}.internal:8002"
      },
      {
        name = "ENVIRONMENT"
        value = var.environment
      }
    ]

    core-service = [
      {
        name  = "DATABASE_URL"
        value = "postgresql://postgres:${var.core_db_password}@${var.core_db_endpoint}:5432/${var.core_db_name}"
      }
    ]

    eeg-service = []
  }

  # Merge base environment variables with dynamic ones from tfvars
  service_envs = {
    for service_key, base_envs in local.base_service_envs : service_key => concat(
      base_envs,
      [
        for key, value in var.ecs_task_env_vars : {
          name  = key
          value = value
        }
      ]
    )
  }
}


locals {
  service_ports = {
    gateway      = 8000
    core-service = 8001
    eeg-service  = 8002
  }
}






#########################################
# 🔹 ECS Task Definitions (per service)
#########################################

# Each ECS Task Definition = “blueprint” for running a container.
# It defines image, ports, CPU, memory, health checks, logging, etc.

resource "aws_ecs_task_definition" "task" {
  for_each = var.service_images  # Creates one per service

  family                   = "${local.name_prefix}-${each.key}"
  network_mode             = "awsvpc"         # Each task gets its own ENI/IP
  requires_compatibilities = ["FARGATE"]      # Run on AWS Fargate (serverless)
  cpu                      = "512"            # 0.5 vCPU
  memory                   = "1024"           # 1 GB memory
  execution_role_arn       = aws_iam_role.task_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  # 🔧 DNS Configuration - PERMANENT FIX for VPC Endpoint DNS resolution
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  # Container configuration for each service
  container_definitions = jsonencode([
    {
      name      = each.key
      image     = each.value                 # ECR image URL
      essential = true
      
      portMappings = [
        {
          containerPort = local.service_ports[each.key]
          hostPort      = local.service_ports[each.key]
          protocol      = "tcp"
        }
      ]

      #  Inject DATABASE_URL dynamically per service + ECS cache control
      environment = concat([
        for env in local.service_envs[each.key] : {
          name  = env.name
          value = env.value
        }
      ], [
        # 🔧 ECS Agent Environment Variables - Prevents DNS caching
        {
          name  = "ECS_ENABLE_CONTAINER_METADATA"
          value = "true"
        },
        {
          name  = "ECS_ENABLE_TASK_IAM_ROLE"
          value = "true"
        },
        {
          name  = "ECS_ENABLE_TASK_IAM_ROLE_NETWORK_HOST"
          value = "true"
        }
      ])

      # Send logs to CloudWatch under /ecs/niura-staging/<service-name>
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = each.key
        }
      }

      # Health check — makes sure container is healthy before sending traffic
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:${local.service_ports[each.key]}/api/health || exit 1"]
        interval    = 30
        retries     = 3
        startPeriod = 60  # 🔧 Increased from 10s to 60s for reliable startup
        timeout     = 5
      }
    }
  ])

   # ✅ Force new task definition when container definitions change
  lifecycle {
    create_before_destroy = true
  }


}



#########################################
# 🔹 Target Groups (one per service)
#########################################

# Each target group represents a backend service the ALB can route to.
# e.g., /gateway → gateway target group

resource "aws_lb_target_group" "tg" {
  for_each = var.service_images

  name         = "${local.name_prefix}-${each.key}-tg"
  port         = local.service_ports[each.key]
  protocol     = "HTTP"
  vpc_id       = var.vpc_id
  target_type  = "ip"  # Each task gets its own private IP

  health_check {
    path                = "/api/health"
    interval            = 15    # Reduced from 30s to 15s (50% faster)
    timeout             = 10    # Increased from 5s to 10s (more reliable)
    healthy_threshold   = 2     # Keep at 2 for reliability
    unhealthy_threshold = 2     # Reduced from 3 to 2 (faster failure detection)
    matcher             = "200-399"
  }
}



#########################################
# 🔹 Listener Rules (Gateway-Only Routing)
#########################################

# ✅ INDUSTRY STANDARD: ALL traffic goes through gateway
# Gateway acts as reverse proxy and routes to internal services
# Core and EEG services are PRIVATE (no direct ALB access)

resource "aws_lb_listener_rule" "gateway_only" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg["gateway"].arn
  }

  condition {
    path_pattern {
      values = ["/*"]  # ALL traffic → Gateway
    }
  }
}



#########################################
# 🔹 ECS Service (one per microservice)
#########################################

# This is what actually runs your containers.
# It ties together:
# - ECS cluster
# - Task definition
# - Target group (ALB routing)
# - Networking (subnets, security groups)

resource "aws_ecs_service" "service" {
  for_each = var.service_images

  name            = "${local.name_prefix}-${each.key}-svc"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.task[each.key].arn
  desired_count   = var.desired_count      # Number of containers to run
  launch_type     = "FARGATE"              # Serverless container runtime

  # Networking — connect containers to subnets and security groups
  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.ecs_sg.id]   # use ecs_sg for tasks
    assign_public_ip = each.key == "gateway" ? true : false  # ✅ Only gateway is public
  }

  # Link the container to its load balancer target group (ONLY for gateway)
  dynamic "load_balancer" {
    for_each = each.key == "gateway" ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.tg[each.key].arn
      container_name   = each.key
      container_port   = local.service_ports[each.key]
    }
  }

  # Register with Cloud Map for service discovery
  service_registries {
    registry_arn = aws_service_discovery_service.sd[each.key].arn
  }

  # Health check grace period - only for gateway (has ALB)
  health_check_grace_period_seconds = each.key == "gateway" ? 60 : null

   # ✅ Force new deployment when task definition changes
  force_new_deployment = true
}

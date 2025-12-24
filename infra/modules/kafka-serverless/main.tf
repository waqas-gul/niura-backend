######################################################
# MODULE: Kafka (Amazon MSK Serverless)
######################################################



# --- Security Group for Kafka Cluster ---
resource "aws_security_group" "kafka_sg" {
  name        = "${var.project_name}-${var.environment}-kafka-sg"
  description = "Security group for MSK Serverless"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-kafka-sg"
  }
}

# --- Allow ECS services to connect to Kafka ---
resource "aws_security_group_rule" "ecs_to_kafka" {
  description              = "Allow ECS tasks to connect to Kafka (TLS)"
  type                     = "ingress"
  from_port                = 9098
  to_port                  = 9098
  protocol                 = "tcp"
  security_group_id        = aws_security_group.kafka_sg.id
  source_security_group_id = var.ecs_security_group_id
}

# --- Allow Bastion to connect to Kafka (for topic creation) ---
resource "aws_security_group_rule" "bastion_to_kafka" {
  count                    = var.bastion_security_group_id != "" ? 1 : 0
  description              = "Allow bastion host to connect to Kafka for admin tasks"
  type                     = "ingress"
  from_port                = 9098
  to_port                  = 9098
  protocol                 = "tcp"
  security_group_id        = aws_security_group.kafka_sg.id
  source_security_group_id = var.bastion_security_group_id
}

# --- Create the Serverless Kafka Cluster ---
resource "aws_msk_serverless_cluster" "this" {
  cluster_name = "${var.project_name}-${var.environment}-msk-sls"

  vpc_config {
    subnet_ids      = var.subnet_ids
    security_group_ids = [ aws_security_group.kafka_sg.id ]  # Note: plural _ids, not security_groups
  }



# MSK Serverless supports only SASL/IAM authentication (no plaintext, no SCRAM)
# Your clients (gateway, core-service, eeg-service) will need IAM-based Kafka auth

  client_authentication {
    sasl {
      iam {
        enabled = true    
      }
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-msk-sls"
    Environment = var.environment
  }
}




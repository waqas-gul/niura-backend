variable "project_name" {}
variable "environment" {}
variable "services" {
  description = "List of microservices to create ECR repositories for"
  type        = list(string)
}

# Create one ECR repo per service
resource "aws_ecr_repository" "repos" {
  for_each = toset(var.services)

  name = "${var.project_name}-${each.value}-${var.environment}"

  image_tag_mutability = "MUTABLE" # allow overwriting for now; set to IMMUTABLE later
  force_delete          = true     # cleanup for dev/staging environments

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Service     = each.value
  }
}

# Outputs (repository URLs)
output "repository_urls" {
  value = {
    for svc, repo in aws_ecr_repository.repos :
    svc => repo.repository_url
  }
  description = "Map of service name -> ECR repository URL"
}

output "db_endpoint" {
  description = "The endpoint of the RDS instance"
  value       = aws_db_instance.this.address
}

output "db_name" {
  value = aws_db_instance.this.db_name
}

###############################################
# Export RDS DB Password (for ECS access)
###############################################
output "db_password" {
  description = "Database password for ECS to connect to RDS"
  value       = var.password
  sensitive   = true
}

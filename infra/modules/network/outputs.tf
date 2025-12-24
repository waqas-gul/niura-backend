output "public_subnets" {
  description = "List of public subnet IDs in the VPC"
  value       = aws_subnet.public[*].id
}

########################################
# 📤 VPC ENDPOINTS MODULE OUTPUTS
########################################

output "ecr_api_endpoint_id" {
  description = "ECR API VPC endpoint ID"
  value       = aws_vpc_endpoint.ecr_api.id
}

output "ecr_dkr_endpoint_id" {
  description = "ECR Docker registry VPC endpoint ID"
  value       = aws_vpc_endpoint.ecr_dkr.id
}

output "sts_endpoint_id" {
  description = "STS VPC endpoint ID"
  value       = aws_vpc_endpoint.sts.id
}

output "s3_endpoint_id" {
  description = "S3 gateway VPC endpoint ID"
  value       = aws_vpc_endpoint.s3.id
}

output "logs_endpoint_id" {
  description = "CloudWatch Logs VPC endpoint ID"
  value       = aws_vpc_endpoint.logs.id
}

output "ssm_endpoint_id" {
  description = "Systems Manager VPC endpoint ID"
  value       = aws_vpc_endpoint.ssm.id
}

output "ssmmessages_endpoint_id" {
  description = "SSM Messages VPC endpoint ID"
  value       = aws_vpc_endpoint.ssmmessages.id
}

output "ec2messages_endpoint_id" {
  description = "EC2 Messages VPC endpoint ID"
  value       = aws_vpc_endpoint.ec2messages.id
}

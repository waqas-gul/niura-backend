variable "env_prefix" {}
variable "vpc_id" {}
variable "subnet_id" {}
variable "ami_id" {}
variable "aws_region" {
  default = "ap-south-1"
}
variable "kafka_cluster_arn" {
  default = ""
  description = "MSK Serverless cluster ARN for IAM permissions"
}

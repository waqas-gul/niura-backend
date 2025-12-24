variable "project_name" { type = string }
variable "environment"  { type = string }
variable "vpc_id"       { type = string }
variable "subnet_ids"   { type = list(string) }
variable "ecs_security_group_id" { type = string }
variable "bastion_security_group_id" { 
  type    = string 
  default = ""
  description = "Bastion security group ID for Kafka admin access"
}

variable "name" { type = string }
variable "db_name" { type = string }
variable "username" { type = string }
variable "subnet_ids" { type = list(string) }
variable "vpc_security_group_ids" { type = list(string) }
variable "instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "allocated_storage" {
     type = number
    default = 20
 }
variable "engine_version" {
     type = string
     default = "17.6" 
 }
variable "publicly_accessible" {
     type = bool
     default = false 
 }
variable "environment" {
     type = string
     default = "staging" 
 }

variable "password" {
  description = "Master password for the RDS PostgreSQL instance"
  type        = string
  sensitive   = true
}

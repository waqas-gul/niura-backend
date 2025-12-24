output "cluster_id" {
  value = aws_ecs_cluster.this.id
}
output "alb_dns" {
  value = aws_lb.alb.dns_name
}
output "service_names" {
  value = [for s in aws_ecs_service.service : s.name]
}

output "alb_security_group_id" {
  description = "Security group ID of the ALB created by ECS module"
  value       = aws_security_group.alb_sg.id
}


output "ecs_security_group_id" {
  description = "Security group ID used by ECS tasks (allows DB access)"
  value       = aws_security_group.ecs_sg.id
}

output "ecs_task_role_id" {
  description = "IAM role ID for ECS task runtime permissions"
  value       = aws_iam_role.ecs_task_role.id
}

output "eeg_worker_service_name" {
  description = "EEG worker service name"
  value       = aws_ecs_service.eeg_worker.name
}

output "eeg_worker_task_definition_arn" {
  description = "EEG worker task definition ARN"
  value       = aws_ecs_task_definition.eeg_worker.arn
}

output "eeg_worker_log_group" {
  description = "EEG worker CloudWatch log group"
  value       = aws_cloudwatch_log_group.eeg_worker.name
}

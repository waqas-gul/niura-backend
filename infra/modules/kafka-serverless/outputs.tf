output "kafka_arn" {
  value = aws_msk_serverless_cluster.this.arn
}

output "kafka_bootstrap_brokers" {
  value = aws_msk_serverless_cluster.this.bootstrap_brokers_sasl_iam
}

output "kafka_security_group_id" {
  value = aws_security_group.kafka_sg.id
}

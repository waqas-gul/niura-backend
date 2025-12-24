aws_region   = "ap-south-1"
aws_profile  = "default"
environment  = "production"
project_name = "niura"

kafka_bootstrap_broker = "boot-prodabcde.c1.kafka-serverless.ap-south-1.amazonaws.com:9098"

ecs_task_env_vars = {
  APP_ENV        = "production"
  KAFKA_BROKER   = "boot-prodabcde.c1.kafka-serverless.ap-south-1.amazonaws.com:9098"
  KAFKA_REGION   = "ap-south-1"
}

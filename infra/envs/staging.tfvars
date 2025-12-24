aws_region   = "ap-south-1"
aws_profile  = "default"
environment  = "staging"
project_name = "niura"

kafka_bootstrap_broker = "boot-mznm5shf.c1.kafka-serverless.ap-south-1.amazonaws.com:9098"

ecs_task_env_vars = {
  APP_ENV        = "staging"
  KAFKA_BROKER   = "boot-mznm5shf.c1.kafka-serverless.ap-south-1.amazonaws.com:9098"
  KAFKA_REGION   = "ap-south-1"
  RAW_EEG_BUCKET = "niura-realtime-raw-eeg"
}
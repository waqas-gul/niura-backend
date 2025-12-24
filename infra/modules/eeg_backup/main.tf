#########################################
# Random suffix to keep bucket names unique
#########################################

# Generates a short random hex ID to append to S3 bucket names.
# S3 bucket names must be globally unique, so this prevents conflicts.
resource "random_id" "suffix" {
  byte_length = 3  # 3 bytes = 6 hex characters
}



#########################################
# 7️⃣ IAM Role for Lambda (write to S3)
#########################################

# Creates an IAM Role that allows a Lambda function to run.
# The trust policy below allows the Lambda service to assume this role.
resource "aws_iam_role" "lambda_role" {
  name = "niura-eeg-backup-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"  # AWS Lambda will use this role
        }
      }
    ]
  })

  tags = {
    Project = "Niura EEG"
    Env     = "dev"
  }
}



#########################################
# 8️⃣ Attach the necessary policies to Lambda Role
#########################################

# Gives the Lambda permission to upload files to S3 buckets and write CloudWatch Logs
resource "aws_iam_role_policy" "lambda_policy" {
  name = "niura-eeg-backup-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::${aws_s3_bucket.daily_backup.bucket}/*",
          "arn:aws:s3:::${aws_s3_bucket.monthly_backup.bucket}/*",
          "arn:aws:s3:::${aws_s3_bucket.yearly_backup.bucket}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      }
    ]
  })
}

# Output the role ARN for reference
output "lambda_role_arn" {
  value       = aws_iam_role.lambda_role.arn
  description = "The ARN of the IAM Role for Lambda"
}



#########################################
# 9️⃣ Lambda Function to Backup Data to S3
#########################################

# Defines the actual AWS Lambda function that performs EEG data backups.
# It uses a pre-zipped file (lambda.zip) that contains the Python code.
resource "aws_lambda_function" "eeg_data_backup" {

  # Lambda source code
  filename      = "${path.module}/lambda.zip"   # Must exist in the same folder or Terraform path
  function_name = "niura-eeg-data-backup"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"  # Python entry point
  runtime       = "python3.11"                      # Runtime environment

  # VPC Configuration - Lambda needs to be in VPC to access RDS
  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.lambda_sg_id]
  }

  # Environment variables passed into the Lambda
  environment {
    variables = {
      DB_HOST              = var.core_db_endpoint
      DB_NAME              = var.core_db_name
      DB_USER              = "postgres"
      DB_PASS              = var.core_db_password
      S3_DAILY_BUCKET      = aws_s3_bucket.daily_backup.bucket
      S3_MONTHLY_BUCKET    = aws_s3_bucket.monthly_backup.bucket
      S3_YEARLY_BUCKET     = aws_s3_bucket.yearly_backup.bucket
      S3_REALTIME_BUCKET   = aws_s3_bucket.realtime_raw.bucket
    }
  }

  # Lambda configuration
  timeout     = 900   # 900 seconds = 15 minutes
  memory_size = 1024  # Increased to 1GB for DB operations

  # Ensure IAM policy is created before Lambda runs
  depends_on = [aws_iam_role_policy.lambda_policy]
}

# Output Lambda function ARN for reference
output "lambda_function_arn" {
  value       = aws_lambda_function.eeg_data_backup.arn
  description = "The ARN of the Lambda function"
}



#########################################
# 🔄 EVENTBRIDGE SCHEDULING FOR LAMBDA
#########################################
# These resources automatically trigger the Lambda on a schedule (daily, monthly, yearly)
# to run periodic data aggregation jobs.



# -------------------------
# 1️⃣ Daily Aggregation Rule
# -------------------------

# Triggers the Lambda once every 24 hours.
resource "aws_cloudwatch_event_rule" "daily_aggregation_rule" {
  name                = "niura-daily-aggregation-rule"
  description         = "Triggers Lambda for daily EEG aggregation"
  schedule_expression = "rate(1 day)"  # Simple rate syntax
}

# Connects the daily rule to the Lambda function
resource "aws_cloudwatch_event_target" "daily_aggregation_target" {
  rule      = aws_cloudwatch_event_rule.daily_aggregation_rule.name
  target_id = "niura-eeg-daily-target"
  arn       = aws_lambda_function.eeg_data_backup.arn

  # Optional: pass JSON payload to Lambda
  input = jsonencode({
    aggregation_type = "daily"
  })
}

# Grants EventBridge permission to invoke the Lambda for daily rule
resource "aws_lambda_permission" "eventbridge_lambda_permission_daily" {
  statement_id  = "AllowEventBridgeInvokeLambdaDaily"
  action        = "lambda:InvokeFunction"
  principal     = "events.amazonaws.com"
  function_name = aws_lambda_function.eeg_data_backup.function_name
  source_arn    = aws_cloudwatch_event_rule.daily_aggregation_rule.arn
}



# -------------------------
# 2️⃣ Monthly Aggregation Rule
# -------------------------

# Triggers Lambda once a month — on the 1st of every month at midnight UTC.
resource "aws_cloudwatch_event_rule" "monthly_aggregation_rule" {
  name                = "niura-monthly-aggregation-rule"
  description         = "Triggers Lambda for monthly EEG aggregation"
  schedule_expression = "cron(0 0 1 * ? *)"
}

# Connects the monthly rule to the Lambda
resource "aws_cloudwatch_event_target" "monthly_aggregation_target" {
  rule      = aws_cloudwatch_event_rule.monthly_aggregation_rule.name
  target_id = "niura-eeg-monthly-target"
  arn       = aws_lambda_function.eeg_data_backup.arn

  input = jsonencode({
    aggregation_type = "monthly"
  })
}

# Grants EventBridge permission to invoke the Lambda for monthly rule
resource "aws_lambda_permission" "eventbridge_lambda_permission_monthly" {
  statement_id  = "AllowEventBridgeInvokeLambdaMonthly"
  action        = "lambda:InvokeFunction"
  principal     = "events.amazonaws.com"
  function_name = aws_lambda_function.eeg_data_backup.function_name
  source_arn    = aws_cloudwatch_event_rule.monthly_aggregation_rule.arn
}



# -------------------------
# 3️⃣ Yearly Aggregation Rule
# -------------------------

# Triggers Lambda once per year — on January 1st at midnight UTC.
resource "aws_cloudwatch_event_rule" "yearly_aggregation_rule" {
  name                = "niura-yearly-aggregation-rule"
  description         = "Triggers Lambda for yearly EEG aggregation"
  schedule_expression = "cron(0 0 1 1 ? *)"
}

# Connects the yearly rule to the Lambda
resource "aws_cloudwatch_event_target" "yearly_aggregation_target" {
  rule      = aws_cloudwatch_event_rule.yearly_aggregation_rule.name
  target_id = "niura-eeg-yearly-target"
  arn       = aws_lambda_function.eeg_data_backup.arn

  input = jsonencode({
    aggregation_type = "yearly"
  })
}

# Grants EventBridge permission to invoke the Lambda for yearly rule
resource "aws_lambda_permission" "eventbridge_lambda_permission_yearly" {
  statement_id  = "AllowEventBridgeInvokeLambdaYearly"
  action        = "lambda:InvokeFunction"
  principal     = "events.amazonaws.com"
  function_name = aws_lambda_function.eeg_data_backup.function_name
  source_arn    = aws_cloudwatch_event_rule.yearly_aggregation_rule.arn
}




resource "aws_s3_bucket" "realtime_raw" {
  bucket = "niura-realtime-raw-eeg"
  force_destroy = true
}

# Daily backup bucket
resource "aws_s3_bucket" "daily_backup" {
  bucket = "niura-eeg-daily-backup-${random_id.suffix.hex}"
  force_destroy = true

  tags = {
    Project = "Niura EEG"
    Env     = "staging"
    Type    = "Daily Backup"
  }
}

resource "aws_s3_bucket_versioning" "daily_backup_versioning" {
  bucket = aws_s3_bucket.daily_backup.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "daily_backup_encryption" {
  bucket = aws_s3_bucket.daily_backup.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "daily_backup_public_access" {
  bucket                  = aws_s3_bucket.daily_backup.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Monthly backup bucket
resource "aws_s3_bucket" "monthly_backup" {
  bucket = "niura-eeg-monthly-backup-${random_id.suffix.hex}"
  force_destroy = true

  tags = {
    Project = "Niura EEG"
    Env     = "staging"
    Type    = "Monthly Backup"
  }
}

resource "aws_s3_bucket_versioning" "monthly_backup_versioning" {
  bucket = aws_s3_bucket.monthly_backup.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "monthly_backup_encryption" {
  bucket = aws_s3_bucket.monthly_backup.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "monthly_backup_public_access" {
  bucket                  = aws_s3_bucket.monthly_backup.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Yearly backup bucket
resource "aws_s3_bucket" "yearly_backup" {
  bucket = "niura-eeg-yearly-backup-${random_id.suffix.hex}"
  force_destroy = true

  tags = {
    Project = "Niura EEG"
    Env     = "staging"
    Type    = "Yearly Backup"
  }
}

resource "aws_s3_bucket_versioning" "yearly_backup_versioning" {
  bucket = aws_s3_bucket.yearly_backup.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "yearly_backup_encryption" {
  bucket = aws_s3_bucket.yearly_backup.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "yearly_backup_public_access" {
  bucket                  = aws_s3_bucket.yearly_backup.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role_policy" "ecs_eeg_realtime_s3" {
  count = var.ecs_task_role_id != "" ? 1 : 0
  name  = "niura-eeg-realtime-s3-policy"
  role  = var.ecs_task_role_id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:PutObject"]
      Resource = "${aws_s3_bucket.realtime_raw.arn}/*"
    }]
  })
}

output "realtime_raw_bucket" {
  value = aws_s3_bucket.realtime_raw.bucket
}

output "daily_backup_bucket" {
  value = aws_s3_bucket.daily_backup.bucket
}

output "monthly_backup_bucket" {
  value = aws_s3_bucket.monthly_backup.bucket
}

output "yearly_backup_bucket" {
  value = aws_s3_bucket.yearly_backup.bucket
}


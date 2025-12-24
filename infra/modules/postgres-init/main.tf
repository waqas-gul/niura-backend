###########################################
# 🔹 PostgreSQL Database Initializer
###########################################

variable "rds_endpoint" { type = string }
variable "db_port" { type = number }
variable "db_name" { type = string }
variable "db_user" { type = string }
variable "db_password" { type = string }

resource "null_resource" "init_db" {
  # wait for the RDS endpoint to exist
  triggers = {
    endpoint = var.rds_endpoint
  }

  provisioner "local-exec" {
    command = <<EOT
echo "🧩 Ensuring database '${var.db_name}' exists on ${var.rds_endpoint}..."

PGPASSWORD="${var.db_password}" \
psql "host=${var.rds_endpoint} port=${var.db_port} user=${var.db_user} dbname=postgres sslmode=require" \
-c "DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '${var.db_name}') THEN
    CREATE DATABASE ${var.db_name} OWNER ${var.db_user};
    RAISE NOTICE 'Database ${var.db_name} created';
  ELSE
    RAISE NOTICE 'Database ${var.db_name} already exists';
  END IF;
END $$;"

echo "✅ Database ${var.db_name} verified."
EOT
  }
}

# =============================================================================
# LCMGoCloud-CAGenAI - RDS PostgreSQL Database
# =============================================================================
# PostgreSQL 15 with extensions for:
# - uuid-ossp: UUID generation
# - pg_trgm: Trigram similarity search (Greek names)
# - unaccent: Accent-insensitive search (Greek)
# - pg_stat_statements: Query performance stats
# - btree_gin: GIN index support
# =============================================================================

# -----------------------------------------------------------------------------
# Random Password for RDS (if not provided)
# -----------------------------------------------------------------------------

resource "random_password" "db_password" {
  count   = var.db_password == "" ? 1 : 0
  length  = 32
  special = true
  # Avoid characters that cause issues in connection strings
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

locals {
  db_password = var.db_password != "" ? var.db_password : random_password.db_password[0].result
}

# -----------------------------------------------------------------------------
# Secrets Manager - Database Credentials
# -----------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${local.name_prefix}-db-credentials"
  description = "PostgreSQL database credentials for ${local.name_prefix}"

  tags = {
    Name = "${local.name_prefix}-db-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = local.db_password
    engine   = "postgres"
    host     = aws_db_instance.main.address
    port     = 5432
    dbname   = var.db_name
  })

  depends_on = [aws_db_instance.main]
}

# -----------------------------------------------------------------------------
# RDS Parameter Group - PostgreSQL 15 with Extensions
# -----------------------------------------------------------------------------

resource "aws_db_parameter_group" "postgres15" {
  name        = "${local.name_prefix}-postgres15-params"
  family      = "postgres15"
  description = "PostgreSQL 15 parameters for ${local.name_prefix}"

  # Enable logging
  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # Log queries > 1 second
  }

  # Performance settings
  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name  = "pg_stat_statements.track"
    value = "all"
  }

  # Greek locale support
  parameter {
    name  = "lc_messages"
    value = "en_US.UTF-8"
  }

  tags = {
    Name = "${local.name_prefix}-postgres15-params"
  }
}

# -----------------------------------------------------------------------------
# RDS PostgreSQL Instance
# -----------------------------------------------------------------------------

resource "aws_db_instance" "main" {
  identifier = "${local.name_prefix}-postgres"

  # Engine
  engine               = "postgres"
  engine_version       = "15.10"
  instance_class       = var.db_instance_class
  parameter_group_name = aws_db_parameter_group.postgres15.name

  # Storage
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = 100 # Enable storage autoscaling up to 100GB
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database
  db_name  = var.db_name
  username = var.db_username
  password = local.db_password
  port     = 5432

  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = var.db_multi_az

  # Backup
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  # Monitoring
  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  monitoring_interval                   = 60
  monitoring_role_arn                   = aws_iam_role.rds_monitoring.arn
  enabled_cloudwatch_logs_exports       = ["postgresql", "upgrade"]

  # Deletion protection
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name_prefix}-postgres-final-snapshot"
  copy_tags_to_snapshot     = true

  # Allow minor version upgrades
  auto_minor_version_upgrade = true

  tags = {
    Name = "${local.name_prefix}-postgres"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# -----------------------------------------------------------------------------
# IAM Role for Enhanced Monitoring
# -----------------------------------------------------------------------------

resource "aws_iam_role" "rds_monitoring" {
  name = "${local.name_prefix}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-rds-monitoring-role"
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms for RDS
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${local.name_prefix}-rds-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization exceeds 80%"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }

  tags = {
    Name = "${local.name_prefix}-rds-high-cpu"
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_storage" {
  alarm_name          = "${local.name_prefix}-rds-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 5368709120 # 5 GB in bytes
  alarm_description   = "RDS free storage below 5GB"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }

  tags = {
    Name = "${local.name_prefix}-rds-low-storage"
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${local.name_prefix}-rds-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 50 # db.t3.small has ~85 max connections
  alarm_description   = "RDS connections exceeds 50"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }

  tags = {
    Name = "${local.name_prefix}-rds-high-connections"
  }
}

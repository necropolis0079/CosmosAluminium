# =============================================================================
# LCMGoCloud-CAGenAI - Database Initialization Lambda
# =============================================================================
# One-time Lambda function to initialize PostgreSQL schema
# Uses pg8000 (pure Python PostgreSQL driver) - no binary dependencies
# =============================================================================

# -----------------------------------------------------------------------------
# Null Resource to Build Lambda Layer
# -----------------------------------------------------------------------------

resource "null_resource" "pg8000_layer_build" {
  triggers = {
    requirements_hash = filemd5("${path.module}/../../lambda/db_init/requirements.txt")
  }

  provisioner "local-exec" {
    command     = <<-EOT
      $ErrorActionPreference = "Stop"
      $layerDir = "${replace(path.module, "/", "\\")}\\..\\..\\lambda\\db_init\\layer"
      $pythonDir = "$layerDir\\python"

      # Create directories
      if (Test-Path $layerDir) { Remove-Item -Recurse -Force $layerDir }
      New-Item -ItemType Directory -Force -Path $pythonDir | Out-Null

      # Install dependencies
      pip install pg8000 -t $pythonDir --quiet --no-cache-dir

      # Create zip
      Compress-Archive -Path "$layerDir\\*" -DestinationPath "${replace(path.module, "/", "\\")}\\..\\..\\lambda\\db_init\\pg8000_layer.zip" -Force

      Write-Host "Layer built successfully"
    EOT
    interpreter = ["powershell", "-Command"]
  }
}

# -----------------------------------------------------------------------------
# Lambda Layer for pg8000
# -----------------------------------------------------------------------------

resource "aws_lambda_layer_version" "pg8000" {
  filename            = "${path.module}/../../lambda/db_init/pg8000_layer.zip"
  layer_name          = "${local.name_prefix}-pg8000"
  description         = "pg8000 PostgreSQL driver for Python"
  compatible_runtimes = ["python3.11", "python3.12"]

  depends_on = [null_resource.pg8000_layer_build]
}

# -----------------------------------------------------------------------------
# Package Lambda Code with SQL Files
# -----------------------------------------------------------------------------

data "archive_file" "db_init_lambda" {
  type        = "zip"
  output_path = "${path.module}/../../lambda/db_init/db_init.zip"

  source {
    content  = file("${path.module}/../../lambda/db_init/handler.py")
    filename = "handler.py"
  }

  # Include SQL files
  dynamic "source" {
    for_each = fileset("${path.module}/../../scripts/sql", "*.sql")
    content {
      content  = file("${path.module}/../../scripts/sql/${source.value}")
      filename = "sql/${source.value}"
    }
  }
}

# -----------------------------------------------------------------------------
# Lambda Function
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "db_init" {
  function_name = "${local.name_prefix}-db-init"
  description   = "One-time database schema initialization"

  filename         = data.archive_file.db_init_lambda.output_path
  source_code_hash = data.archive_file.db_init_lambda.output_base64sha256

  handler     = "handler.handler"
  runtime     = "python3.11"
  timeout     = 300 # 5 minutes for schema creation
  memory_size = 256

  role = aws_iam_role.lambda_execution.arn

  # VPC configuration to access RDS
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  # Use pg8000 layer
  layers = [aws_lambda_layer_version.pg8000.arn]

  environment {
    variables = {
      DB_SECRET_ARN = aws_secretsmanager_secret.db_credentials.arn
      DB_NAME       = var.db_name
    }
  }

  tags = {
    Name    = "${local.name_prefix}-db-init"
    Purpose = "one-time-initialization"
  }

  depends_on = [
    aws_db_instance.main,
    aws_secretsmanager_secret_version.db_credentials,
    null_resource.pg8000_layer_build
  ]
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "db_init" {
  name              = "/aws/lambda/${local.name_prefix}-db-init"
  retention_in_days = 7

  tags = {
    Name = "${local.name_prefix}-db-init-logs"
  }
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "db_init_lambda_name" {
  description = "Name of the database initialization Lambda"
  value       = aws_lambda_function.db_init.function_name
}

output "db_init_lambda_arn" {
  description = "ARN of the database initialization Lambda"
  value       = aws_lambda_function.db_init.arn
}

output "db_init_invoke_command" {
  description = "AWS CLI command to invoke the database initialization"
  value       = <<-EOT
    aws lambda invoke --function-name ${aws_lambda_function.db_init.function_name} --payload "{}" --region ${data.aws_region.current.name} response.json && type response.json
  EOT
}

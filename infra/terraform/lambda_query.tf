# =============================================================================
# Query Lambda
# =============================================================================
# Exposes Text-to-SQL functionality via API.
# Translates natural language HR queries (Greek/English) into PostgreSQL queries.
#
# Supports direct invocation and API Gateway integration.
# Uses Claude Haiku for fast query translation.
# =============================================================================

# -----------------------------------------------------------------------------
# Lambda Function
# -----------------------------------------------------------------------------

data "archive_file" "query" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/query/handler.py"
  output_path = "${path.module}/../../lambda/query/query.zip"
}

resource "aws_lambda_function" "query" {
  filename         = data.archive_file.query.output_path
  source_code_hash = data.archive_file.query.output_base64sha256
  function_name    = "lcmgo-cagenai-prod-query"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.handler"
  runtime          = "python3.11"
  timeout          = 180  # 3 minutes for query translation + SQL execution + HR analysis
  memory_size      = 512

  # Use latest layer versions (data sources to avoid version drift)
  layers = [
    data.aws_lambda_layer_version.lcmgo_package_latest.arn,
    aws_lambda_layer_version.pg8000.arn,
  ]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DB_SECRET_ARN     = aws_secretsmanager_secret.db_credentials.arn
      QUERY_CACHE_TABLE = aws_dynamodb_table.query_cache.name
      AWS_REGION_NAME   = var.aws_region
    }
  }

  tags = merge(local.common_tags, {
    Name = "lcmgo-cagenai-prod-query"
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "query" {
  name              = "/aws/lambda/lcmgo-cagenai-prod-query"
  retention_in_days = 30

  tags = merge(local.common_tags, {
    Name = "lcmgo-cagenai-prod-query-logs"
  })
}

# -----------------------------------------------------------------------------
# IAM Policies for Query Lambda
# -----------------------------------------------------------------------------

# Bedrock access for Claude Haiku (query translation)
resource "aws_iam_role_policy" "query_bedrock" {
  name = "lcmgo-cagenai-prod-query-bedrock"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          # Claude Haiku for query translation
          "arn:aws:bedrock:eu-north-1::foundation-model/eu.anthropic.claude-haiku-4-5-20251001-v1:0",
          # Sonnet as fallback
          "arn:aws:bedrock:eu-north-1::foundation-model/eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
        ]
      }
    ]
  })
}

# Secrets Manager access for DB credentials
resource "aws_iam_role_policy" "query_secrets" {
  name = "lcmgo-cagenai-prod-query-secrets"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.db_credentials.arn
      }
    ]
  })
}

# DynamoDB access for query cache
resource "aws_iam_role_policy" "query_dynamodb" {
  name = "lcmgo-cagenai-prod-query-dynamodb"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.query_cache.arn,
          "${aws_dynamodb_table.query_cache.arn}/index/*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Lambda Function URL (for direct HTTP access without API Gateway)
# -----------------------------------------------------------------------------

resource "aws_lambda_function_url" "query" {
  function_name      = aws_lambda_function.query.function_name
  authorization_type = "AWS_IAM"  # Requires IAM authentication

  cors {
    allow_credentials = true
    allow_headers     = ["content-type", "authorization"]
    allow_methods     = ["*"]
    allow_origins     = ["*"]  # Restrict in production
    max_age           = 86400
  }
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "query_errors" {
  alarm_name          = "lcmgo-cagenai-prod-query-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Query Lambda errors exceed threshold"

  dimensions = {
    FunctionName = aws_lambda_function.query.function_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "query_duration" {
  alarm_name          = "lcmgo-cagenai-prod-query-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 10000  # 10 seconds
  alarm_description   = "Query Lambda duration exceeds threshold"

  dimensions = {
    FunctionName = aws_lambda_function.query.function_name
  }

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "query_lambda_arn" {
  description = "ARN of the Query Lambda function"
  value       = aws_lambda_function.query.arn
}

output "query_lambda_name" {
  description = "Name of the Query Lambda function"
  value       = aws_lambda_function.query.function_name
}

output "query_lambda_url" {
  description = "Function URL for Query Lambda"
  value       = aws_lambda_function_url.query.function_url
}

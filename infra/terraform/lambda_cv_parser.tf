# =============================================================================
# CV Parser Lambda
# =============================================================================
# Parses extracted CV text using Claude Sonnet 4.5 into structured data.
# Writes to PostgreSQL and indexes to OpenSearch.
#
# Triggered asynchronously by cv_processor Lambda.
# =============================================================================

# -----------------------------------------------------------------------------
# Lambda Function
# -----------------------------------------------------------------------------

data "archive_file" "cv_parser" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/cv_parser/handler.py"
  output_path = "${path.module}/../../lambda/cv_parser/cv_parser.zip"
}

resource "aws_lambda_function" "cv_parser" {
  filename         = data.archive_file.cv_parser.output_path
  source_code_hash = data.archive_file.cv_parser.output_base64sha256
  function_name    = "lcmgo-cagenai-prod-cv-parser"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.handler"
  runtime          = "python3.11"
  timeout          = 300 # 5 minutes for Claude API calls
  memory_size      = 1024

  # Use existing layers
  layers = [
    aws_lambda_layer_version.lcmgo_package.arn,
    aws_lambda_layer_version.pg8000.arn,
    aws_lambda_layer_version.opensearch.arn,
  ]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      PROCESSED_BUCKET    = aws_s3_bucket.processed_data.bucket
      STATE_TABLE         = aws_dynamodb_table.cv_processing_state.name
      DB_SECRET_ARN       = aws_secretsmanager_secret.db_credentials.arn
      OPENSEARCH_ENDPOINT = aws_opensearch_domain.main.endpoint
      AWS_REGION_NAME     = var.aws_region
    }
  }

  tags = merge(local.common_tags, {
    Name = "lcmgo-cagenai-prod-cv-parser"
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "cv_parser" {
  name              = "/aws/lambda/lcmgo-cagenai-prod-cv-parser"
  retention_in_days = 30

  tags = merge(local.common_tags, {
    Name = "lcmgo-cagenai-prod-cv-parser-logs"
  })
}

# -----------------------------------------------------------------------------
# IAM Policies for CV Parser
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy" "cv_parser_s3" {
  name = "lcmgo-cagenai-prod-cv-parser-s3"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "${aws_s3_bucket.processed_data.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "${aws_s3_bucket.processed_data.arn}/parsed/*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "cv_parser_bedrock" {
  name = "lcmgo-cagenai-prod-cv-parser-bedrock"
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
          # EU cross-region inference profiles route to various EU regions
          # Use wildcard for region since eu. profiles route to eu-west-3, eu-central-1, etc.
          "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/eu.anthropic.claude-*",
          "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/eu.cohere.embed-*",
          # Foundation models in all EU regions (for cross-region inference)
          "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-5-*",
          "arn:aws:bedrock:*::foundation-model/anthropic.claude-opus-4-5-*",
          "arn:aws:bedrock:*::foundation-model/cohere.embed-*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "cv_parser_secrets" {
  name = "lcmgo-cagenai-prod-cv-parser-secrets"
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

resource "aws_iam_role_policy" "cv_parser_opensearch" {
  name = "lcmgo-cagenai-prod-cv-parser-opensearch"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "es:ESHttpGet",
          "es:ESHttpPost",
          "es:ESHttpPut",
          "es:ESHttpDelete"
        ]
        Resource = "${aws_opensearch_domain.main.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "cv_parser_dynamodb" {
  name = "lcmgo-cagenai-prod-cv-parser-dynamodb"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.cv_processing_state.arn
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Permission for cv_processor to invoke cv_parser
# -----------------------------------------------------------------------------

resource "aws_lambda_permission" "cv_processor_invoke_parser" {
  statement_id  = "AllowCVProcessorInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cv_parser.function_name
  principal     = "lambda.amazonaws.com"
  source_arn    = aws_lambda_function.cv_processor.arn
}

# Add invoke permission to cv_processor's role
resource "aws_iam_role_policy" "cv_processor_invoke_parser" {
  name = "lcmgo-cagenai-prod-cv-processor-invoke-parser"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
          "lambda:InvokeAsync"
        ]
        Resource = aws_lambda_function.cv_parser.arn
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "cv_parser_lambda_arn" {
  description = "ARN of the CV parser Lambda function"
  value       = aws_lambda_function.cv_parser.arn
}

output "cv_parser_lambda_name" {
  description = "Name of the CV parser Lambda function"
  value       = aws_lambda_function.cv_parser.function_name
}

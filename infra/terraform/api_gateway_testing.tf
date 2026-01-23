# =============================================================================
# LCMGoCloud-CAGenAI - API Gateway Testing Routes
# =============================================================================
# Testing endpoints for the frontend UI (no authentication required).
# WARNING: These routes are for testing only - disable in production!
#
# Endpoints:
#   POST /test/upload                  - Generate presigned S3 URL
#   GET  /test/status/{id}             - Poll processing status
#   POST /test/query                   - Text-to-SQL query (no auth)
#   GET  /test/candidates              - List all candidates from database
#   GET  /test/candidates/{id}         - Get single candidate
#   DELETE /test/candidates/{id}       - Delete candidate
#
# Created: 2026-01-19 (Session 35)
# Updated: 2026-01-19 - Added candidates API
# =============================================================================

# -----------------------------------------------------------------------------
# Upload Lambda Function
# -----------------------------------------------------------------------------

data "archive_file" "upload" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/upload/handler.py"
  output_path = "${path.module}/../../lambda/upload/upload.zip"
}

resource "aws_lambda_function" "upload" {
  filename         = data.archive_file.upload.output_path
  source_code_hash = data.archive_file.upload.output_base64sha256
  function_name    = "${local.name_prefix}-upload"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.handler"
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      CV_UPLOADS_BUCKET = aws_s3_bucket.cv_uploads.id
      STATE_TABLE       = aws_dynamodb_table.cv_processing_state.name
      AWS_REGION_NAME   = var.aws_region
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-upload"
  })
}

resource "aws_cloudwatch_log_group" "upload" {
  name              = "/aws/lambda/${local.name_prefix}-upload"
  retention_in_days = 14

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-upload-logs"
  })
}

# -----------------------------------------------------------------------------
# Status Lambda Function
# -----------------------------------------------------------------------------

data "archive_file" "status" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/status/handler.py"
  output_path = "${path.module}/../../lambda/status/status.zip"
}

resource "aws_lambda_function" "status" {
  filename         = data.archive_file.status.output_path
  source_code_hash = data.archive_file.status.output_base64sha256
  function_name    = "${local.name_prefix}-status"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.handler"
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      STATE_TABLE = aws_dynamodb_table.cv_processing_state.name
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-status"
  })
}

resource "aws_cloudwatch_log_group" "status" {
  name              = "/aws/lambda/${local.name_prefix}-status"
  retention_in_days = 14

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-status-logs"
  })
}

# -----------------------------------------------------------------------------
# Candidates Lambda Function
# -----------------------------------------------------------------------------

data "archive_file" "candidates" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/candidates/handler.py"
  output_path = "${path.module}/../../lambda/candidates/candidates.zip"
}

resource "aws_lambda_function" "candidates" {
  filename         = data.archive_file.candidates.output_path
  source_code_hash = data.archive_file.candidates.output_base64sha256
  function_name    = "${local.name_prefix}-candidates"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  layers = [
    aws_lambda_layer_version.pg8000.arn,
  ]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DB_SECRET_ARN        = aws_secretsmanager_secret.db_credentials.arn
      DB_HOST              = aws_db_instance.main.address
      DB_NAME              = aws_db_instance.main.db_name
      DB_PORT              = tostring(aws_db_instance.main.port)
      AWS_REGION_NAME      = var.aws_region
      CV_UPLOADS_BUCKET    = aws_s3_bucket.cv_uploads.id
      STATE_TABLE          = aws_dynamodb_table.cv_processing_state.name
      CLOUDFRONT_DOMAIN    = aws_cloudfront_distribution.cv_uploads.domain_name
      USE_CLOUDFRONT       = "false"  # Disabled: OAC conflicts with presigned URL auth
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-candidates"
  })
}

resource "aws_cloudwatch_log_group" "candidates" {
  name              = "/aws/lambda/${local.name_prefix}-candidates"
  retention_in_days = 14

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-candidates-logs"
  })
}

# -----------------------------------------------------------------------------
# Lambda Integrations for Testing
# -----------------------------------------------------------------------------

# Upload Lambda Integration
resource "aws_apigatewayv2_integration" "upload" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.upload.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# Status Lambda Integration
resource "aws_apigatewayv2_integration" "status" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.status.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# Query Integration (reuse existing query Lambda, no auth)
resource "aws_apigatewayv2_integration" "test_query" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.query.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# Candidates Lambda Integration
resource "aws_apigatewayv2_integration" "candidates" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.candidates.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# -----------------------------------------------------------------------------
# Testing Routes (No Authentication)
# -----------------------------------------------------------------------------

# POST /test/upload - Generate presigned URL
resource "aws_apigatewayv2_route" "test_upload" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /test/upload"
  target    = "integrations/${aws_apigatewayv2_integration.upload.id}"

  authorization_type = "NONE"
}

# GET /test/status/{correlation_id} - Poll processing status
resource "aws_apigatewayv2_route" "test_status" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /test/status/{correlation_id}"
  target    = "integrations/${aws_apigatewayv2_integration.status.id}"

  authorization_type = "NONE"
}

# POST /test/query - Text-to-SQL query (no auth for testing)
resource "aws_apigatewayv2_route" "test_query" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /test/query"
  target    = "integrations/${aws_apigatewayv2_integration.test_query.id}"

  authorization_type = "NONE"
}

# GET /test/candidates - List all candidates
resource "aws_apigatewayv2_route" "test_candidates_list" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /test/candidates"
  target    = "integrations/${aws_apigatewayv2_integration.candidates.id}"

  authorization_type = "NONE"
}

# GET /test/candidates/{candidate_id} - Get single candidate
resource "aws_apigatewayv2_route" "test_candidates_get" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /test/candidates/{candidate_id}"
  target    = "integrations/${aws_apigatewayv2_integration.candidates.id}"

  authorization_type = "NONE"
}

# DELETE /test/candidates/{candidate_id} - Delete candidate
resource "aws_apigatewayv2_route" "test_candidates_delete" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "DELETE /test/candidates/{candidate_id}"
  target    = "integrations/${aws_apigatewayv2_integration.candidates.id}"

  authorization_type = "NONE"
}

# GET /test/candidates/{candidate_id}/cv - Get presigned URL for original CV file
resource "aws_apigatewayv2_route" "test_candidates_cv" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /test/candidates/{candidate_id}/cv"
  target    = "integrations/${aws_apigatewayv2_integration.candidates.id}"

  authorization_type = "NONE"
}

# -----------------------------------------------------------------------------
# Lambda Permissions for API Gateway
# -----------------------------------------------------------------------------

resource "aws_lambda_permission" "api_gateway_upload" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_status" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.status.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_candidates" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.candidates.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Query Lambda already has permission from api_gateway.tf

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "test_upload_url" {
  description = "Testing upload endpoint URL"
  value       = "${aws_apigatewayv2_api.main.api_endpoint}/v1/test/upload"
}

output "test_status_url" {
  description = "Testing status endpoint URL pattern"
  value       = "${aws_apigatewayv2_api.main.api_endpoint}/v1/test/status/{correlation_id}"
}

output "test_query_url" {
  description = "Testing query endpoint URL"
  value       = "${aws_apigatewayv2_api.main.api_endpoint}/v1/test/query"
}

output "test_candidates_url" {
  description = "Testing candidates endpoint URL"
  value       = "${aws_apigatewayv2_api.main.api_endpoint}/v1/test/candidates"
}

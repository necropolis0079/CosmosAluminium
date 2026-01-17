# =============================================================================
# LCMGoCloud-CAGenAI - API Gateway (HTTP API v2)
# =============================================================================
# HTTP API v2 for exposing Lambda functions to the React frontend.
# Uses Cognito JWT authorization for authenticated endpoints.
#
# Endpoints:
#   GET  /health  - Health check (no auth)
#   POST /query   - Text-to-SQL queries (requires auth + query.execute scope)
#
# Rate Limits:
#   - Default: 50 req/sec, 100 burst
#   - /query: 10 req/sec, 20 burst (cost protection for LLM calls)
# =============================================================================

# -----------------------------------------------------------------------------
# HTTP API
# -----------------------------------------------------------------------------

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"
  description   = "LCMGoCloud CA GenAI API - HR Assistant"

  cors_configuration {
    allow_origins = [
      "http://localhost:3000",
      "https://${local.name_prefix}.amplifyapp.com"
    ]
    allow_methods     = ["GET", "POST", "OPTIONS"]
    allow_headers     = ["Content-Type", "Authorization", "X-Request-ID"]
    expose_headers    = ["X-Request-ID", "X-Amzn-Trace-Id"]
    max_age           = 86400
    allow_credentials = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api"
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group for API Access Logs
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.name_prefix}-api"
  retention_in_days = 30

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-logs"
  })
}

# -----------------------------------------------------------------------------
# API Stage (v1)
# -----------------------------------------------------------------------------

resource "aws_apigatewayv2_stage" "v1" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "v1"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId          = "$context.requestId"
      ip                 = "$context.identity.sourceIp"
      requestTime        = "$context.requestTime"
      httpMethod         = "$context.httpMethod"
      routeKey           = "$context.routeKey"
      status             = "$context.status"
      responseLength     = "$context.responseLength"
      integrationError   = "$context.integrationErrorMessage"
      protocol           = "$context.protocol"
      integrationLatency = "$context.integrationLatency"
      responseLatency    = "$context.responseLatency"
      userAgent          = "$context.identity.userAgent"
      authorizerError    = "$context.authorizer.error"
    })
  }

  # Default throttling limits (apply to all routes)
  # Rate limiting: 50 req/sec default, reduced for query via Lambda code if needed
  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-v1"
  })

  # Ensure routes are created before the stage
  depends_on = [
    aws_apigatewayv2_route.health,
    aws_apigatewayv2_route.query
  ]
}

# -----------------------------------------------------------------------------
# Cognito JWT Authorizer
# -----------------------------------------------------------------------------

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  name             = "${local.name_prefix}-cognito-authorizer"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.web.id]
    issuer   = "https://${aws_cognito_user_pool.main.endpoint}"
  }
}

# -----------------------------------------------------------------------------
# Health Lambda Function
# -----------------------------------------------------------------------------

data "archive_file" "health" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/health/handler.py"
  output_path = "${path.module}/../../lambda/health/health.zip"
}

resource "aws_lambda_function" "health" {
  filename         = data.archive_file.health.output_path
  source_code_hash = data.archive_file.health.output_base64sha256
  function_name    = "${local.name_prefix}-health"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.handler"
  runtime          = "python3.11"
  timeout          = 5
  memory_size      = 128

  environment {
    variables = {
      SERVICE_NAME = "lcmgo-cagenai"
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-health"
  })
}

resource "aws_cloudwatch_log_group" "health" {
  name              = "/aws/lambda/${local.name_prefix}-health"
  retention_in_days = 14

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-health-logs"
  })
}

# -----------------------------------------------------------------------------
# Lambda Integrations
# -----------------------------------------------------------------------------

# Health Lambda Integration
resource "aws_apigatewayv2_integration" "health" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.health.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# Query Lambda Integration
resource "aws_apigatewayv2_integration" "query" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.query.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

# Health endpoint (no auth required)
resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.health.id}"

  # No authorization
  authorization_type = "NONE"
}

# Query endpoint (requires JWT auth with query.execute scope)
resource "aws_apigatewayv2_route" "query" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /query"
  target    = "integrations/${aws_apigatewayv2_integration.query.id}"

  authorization_type   = "JWT"
  authorizer_id        = aws_apigatewayv2_authorizer.cognito.id
  authorization_scopes = ["api/query.execute"]
}

# -----------------------------------------------------------------------------
# Lambda Permissions for API Gateway
# -----------------------------------------------------------------------------

resource "aws_lambda_permission" "api_gateway_health" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.health.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_query" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms
# -----------------------------------------------------------------------------

# 5XX Errors Alarm
resource "aws_cloudwatch_metric_alarm" "api_5xx_errors" {
  alarm_name          = "${local.name_prefix}-api-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5xx"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "API Gateway 5XX errors exceed threshold"

  dimensions = {
    ApiId = aws_apigatewayv2_api.main.id
    Stage = aws_apigatewayv2_stage.v1.name
  }

  tags = local.common_tags
}

# Latency Alarm
resource "aws_cloudwatch_metric_alarm" "api_latency" {
  alarm_name          = "${local.name_prefix}-api-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = 300
  extended_statistic  = "p95"
  threshold           = 5000 # 5 seconds
  alarm_description   = "API Gateway p95 latency exceeds 5 seconds"

  dimensions = {
    ApiId = aws_apigatewayv2_api.main.id
    Stage = aws_apigatewayv2_stage.v1.name
  }

  tags = local.common_tags
}

# Throttling Alarm
resource "aws_cloudwatch_metric_alarm" "api_throttling" {
  alarm_name          = "${local.name_prefix}-api-throttling"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Count"
  namespace           = "AWS/ApiGateway"
  period              = 60
  statistic           = "Sum"
  threshold           = 50
  alarm_description   = "API Gateway throttling requests"

  dimensions = {
    ApiId = aws_apigatewayv2_api.main.id
    Stage = aws_apigatewayv2_stage.v1.name
  }

  tags = local.common_tags
}

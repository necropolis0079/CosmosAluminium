# =============================================================================
# LCMGoCloud-CAGenAI - DynamoDB Tables
# =============================================================================
# DynamoDB tables for:
# - CV Processing State Machine (tracking OCR, parsing, storage stages)
# - Query Cache (LLM response caching)
# - User Sessions (Cognito session data)
# =============================================================================

# -----------------------------------------------------------------------------
# CV Processing State Machine Table
# -----------------------------------------------------------------------------
# Tracks CV processing through all stages:
# UPLOADED -> OCR_PROCESSING -> PARSING -> POSTGRES_WRITING -> VECTOR_WRITING -> COMPLETED
# See: docs/13-OBSERVABILITY.md for full state machine diagram
# -----------------------------------------------------------------------------

resource "aws_dynamodb_table" "cv_processing_state" {
  name         = "${local.name_prefix}-cv-processing-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cv_id"

  # Primary key
  attribute {
    name = "cv_id"
    type = "S"
  }

  # GSI attributes
  attribute {
    name = "correlation_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "updated_at"
    type = "S"
  }

  # GSI-1: Look up by correlation ID (for distributed tracing)
  global_secondary_index {
    name            = "correlation_id-index"
    hash_key        = "correlation_id"
    projection_type = "ALL"
  }

  # GSI-2: Query by status + updated_at (for monitoring dashboards)
  global_secondary_index {
    name            = "status-updated_at-index"
    hash_key        = "status"
    range_key       = "updated_at"
    projection_type = "ALL"
  }

  # Enable TTL for automatic cleanup (30 days after completion)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name    = "${local.name_prefix}-cv-processing-state"
    Purpose = "CV processing state machine"
  }
}

# -----------------------------------------------------------------------------
# Query Cache Table
# -----------------------------------------------------------------------------
# Caches LLM responses to reduce Bedrock costs
# TTL-based expiration for cache invalidation
# -----------------------------------------------------------------------------

resource "aws_dynamodb_table" "query_cache" {
  name         = "${local.name_prefix}-query-cache"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cache_key"

  attribute {
    name = "cache_key"
    type = "S"
  }

  # TTL for cache expiration
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name    = "${local.name_prefix}-query-cache"
    Purpose = "LLM response caching"
  }
}

# -----------------------------------------------------------------------------
# User Sessions Table
# -----------------------------------------------------------------------------
# Stores user session data (query history, preferences, saved searches)
# -----------------------------------------------------------------------------

resource "aws_dynamodb_table" "user_sessions" {
  name         = "${local.name_prefix}-user-sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "session_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  # TTL for session expiration
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name    = "${local.name_prefix}-user-sessions"
    Purpose = "User session management"
  }
}

# -----------------------------------------------------------------------------
# Prompt Versions Table
# -----------------------------------------------------------------------------
# Stores prompt templates with version history for A/B testing
# See: docs/14-LLM-ABSTRACTION.md for prompt versioning system
# -----------------------------------------------------------------------------

resource "aws_dynamodb_table" "prompt_versions" {
  name         = "${local.name_prefix}-prompt-versions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "prompt_id"
  range_key    = "version"

  attribute {
    name = "prompt_id"
    type = "S"
  }

  attribute {
    name = "version"
    type = "S"
  }

  attribute {
    name = "is_active"
    type = "S"
  }

  # GSI: Find active version of each prompt
  global_secondary_index {
    name            = "active-prompts-index"
    hash_key        = "prompt_id"
    range_key       = "is_active"
    projection_type = "ALL"
  }

  # Point-in-time recovery for prompt history
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name    = "${local.name_prefix}-prompt-versions"
    Purpose = "LLM prompt version control"
  }
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms for DynamoDB
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "dynamodb_throttle_cv_state" {
  alarm_name          = "${local.name_prefix}-dynamodb-cv-state-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "DynamoDB CV processing state table throttling"

  dimensions = {
    TableName = aws_dynamodb_table.cv_processing_state.name
  }

  tags = {
    Name = "${local.name_prefix}-dynamodb-cv-state-throttle"
  }
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_errors_cv_state" {
  alarm_name          = "${local.name_prefix}-dynamodb-cv-state-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "SystemErrors"
  namespace           = "AWS/DynamoDB"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "DynamoDB CV processing state table system errors"

  dimensions = {
    TableName = aws_dynamodb_table.cv_processing_state.name
  }

  tags = {
    Name = "${local.name_prefix}-dynamodb-cv-state-errors"
  }
}

# =============================================================================
# LCMGoCloud-CAGenAI - IAM Roles and Policies
# =============================================================================

# -----------------------------------------------------------------------------
# Lambda Execution Role
# -----------------------------------------------------------------------------

resource "aws_iam_role" "lambda_execution" {
  name = "${local.name_prefix}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-lambda-execution-role"
  }
}

# -----------------------------------------------------------------------------
# Lambda Basic Execution Policy (CloudWatch Logs)
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# -----------------------------------------------------------------------------
# Lambda VPC Access Policy
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# -----------------------------------------------------------------------------
# Custom Policy - S3 Access
# -----------------------------------------------------------------------------

resource "aws_iam_policy" "lambda_s3_access" {
  name        = "${local.name_prefix}-lambda-s3-policy"
  description = "Allow Lambda to access S3 buckets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ReadWrite"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${local.name_prefix}-*",
          "arn:aws:s3:::${local.name_prefix}-*/*"
        ]
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-lambda-s3-policy"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_s3_access.arn
}

# -----------------------------------------------------------------------------
# Custom Policy - DynamoDB Access
# -----------------------------------------------------------------------------

resource "aws_iam_policy" "lambda_dynamodb_access" {
  name        = "${local.name_prefix}-lambda-dynamodb-policy"
  description = "Allow Lambda to access DynamoDB tables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          "arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${local.name_prefix}-*"
        ]
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-lambda-dynamodb-policy"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb_access" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_dynamodb_access.arn
}

# -----------------------------------------------------------------------------
# Custom Policy - Bedrock Access (EU Cross-Region Inference Profiles)
# -----------------------------------------------------------------------------
# NOTE: eu-north-1 has limited direct model availability.
# We use EU inference profiles which route to available EU regions.
# See: docs/DECISIONS.md - "Bedrock Model Availability in eu-north-1"
# -----------------------------------------------------------------------------

resource "aws_iam_policy" "lambda_bedrock_access" {
  name        = "${local.name_prefix}-lambda-bedrock-policy"
  description = "Allow Lambda to access Amazon Bedrock via EU inference profiles"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockInvokeInferenceProfiles"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          # EU Inference Profiles for Claude models
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/eu.anthropic.claude-sonnet-4-5-*",
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/eu.anthropic.claude-opus-4-5-*",
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/eu.anthropic.claude-3-*",
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/eu.anthropic.claude-haiku-*",
          # EU Inference Profile for Cohere Embed v4
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/eu.cohere.embed-*"
        ]
      },
      {
        Sid    = "BedrockGetInferenceProfile"
        Effect = "Allow"
        Action = [
          "bedrock:GetInferenceProfile",
          "bedrock:ListInferenceProfiles"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-lambda-bedrock-policy"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_bedrock_access" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_bedrock_access.arn
}

# -----------------------------------------------------------------------------
# Custom Policy - Textract Access (for OCR)
# -----------------------------------------------------------------------------

resource "aws_iam_policy" "lambda_textract_access" {
  name        = "${local.name_prefix}-lambda-textract-policy"
  description = "Allow Lambda to access AWS Textract"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "TextractAnalyze"
        Effect = "Allow"
        Action = [
          "textract:DetectDocumentText",
          "textract:AnalyzeDocument"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-lambda-textract-policy"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_textract_access" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_textract_access.arn
}

# -----------------------------------------------------------------------------
# Custom Policy - Secrets Manager Access (for DB credentials)
# -----------------------------------------------------------------------------

resource "aws_iam_policy" "lambda_secrets_access" {
  name        = "${local.name_prefix}-lambda-secrets-policy"
  description = "Allow Lambda to access Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SecretsManagerRead"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}-*"
        ]
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-lambda-secrets-policy"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_secrets_access" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_secrets_access.arn
}

# -----------------------------------------------------------------------------
# Custom Policy - OpenSearch Access
# -----------------------------------------------------------------------------

resource "aws_iam_policy" "lambda_opensearch_access" {
  name        = "${local.name_prefix}-lambda-opensearch-policy"
  description = "Allow Lambda to access OpenSearch"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "OpenSearchAccess"
        Effect = "Allow"
        Action = [
          "es:ESHttpGet",
          "es:ESHttpPost",
          "es:ESHttpPut",
          "es:ESHttpDelete"
        ]
        Resource = [
          "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${local.name_prefix}-*/*"
        ]
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-lambda-opensearch-policy"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_opensearch_access" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_opensearch_access.arn
}

# -----------------------------------------------------------------------------
# Custom Policy - CloudWatch Metrics (for custom metrics)
# -----------------------------------------------------------------------------

resource "aws_iam_policy" "lambda_cloudwatch_metrics" {
  name        = "${local.name_prefix}-lambda-cloudwatch-policy"
  description = "Allow Lambda to publish CloudWatch metrics"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "LCMGoCAGenAI"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-lambda-cloudwatch-policy"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_cloudwatch_metrics" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.lambda_cloudwatch_metrics.arn
}

# =============================================================================
# CV Processor Lambda
# =============================================================================
# Processes uploaded CVs using smart extraction routing:
# - DOCX/Text PDF: Direct extraction (fast, free)
# - Scanned PDF/Images: Triple OCR (Claude Vision + Tesseract + Textract)
# =============================================================================

# -----------------------------------------------------------------------------
# Lambda Layer for CV processing dependencies
# -----------------------------------------------------------------------------

resource "null_resource" "cv_processor_layer_build" {
  triggers = {
    requirements_hash = filemd5("${path.module}/../../lambda/cv_processor/requirements.txt")
    dockerfile_hash   = filemd5("${path.module}/../../lambda/cv_processor/Dockerfile.layer")
  }

  provisioner "local-exec" {
    command     = "powershell -ExecutionPolicy Bypass -File build-layer.ps1"
    working_dir = "${path.module}/../../lambda/cv_processor"
  }
}

resource "aws_lambda_layer_version" "cv_processor" {
  filename            = "${path.module}/../../lambda/cv_processor/cv_processor_layer.zip"
  layer_name          = "lcmgo-cagenai-prod-cv-processor"
  description         = "CV processor dependencies: python-docx, pdfplumber, Pillow"
  compatible_runtimes = ["python3.11", "python3.12"]

  depends_on = [null_resource.cv_processor_layer_build]

  lifecycle {
    create_before_destroy = true
  }
}

# -----------------------------------------------------------------------------
# Lambda Layer for source package (lcmgo_cagenai)
# -----------------------------------------------------------------------------

resource "null_resource" "lcmgo_package_layer_build" {
  triggers = {
    # OCR module
    ocr_init       = filemd5("${path.module}/../../src/lcmgo_cagenai/ocr/__init__.py")
    ocr_extractor  = filemd5("${path.module}/../../src/lcmgo_cagenai/ocr/extractor.py")
    ocr_docx       = filemd5("${path.module}/../../src/lcmgo_cagenai/ocr/docx_extractor.py")
    ocr_pdf        = filemd5("${path.module}/../../src/lcmgo_cagenai/ocr/pdf_extractor.py")
    ocr_triple     = filemd5("${path.module}/../../src/lcmgo_cagenai/ocr/triple_ocr.py")

    # LLM module
    llm_init     = filemd5("${path.module}/../../src/lcmgo_cagenai/llm/__init__.py")
    llm_provider = filemd5("${path.module}/../../src/lcmgo_cagenai/llm/provider.py")

    # Search module
    search_init     = filemd5("${path.module}/../../src/lcmgo_cagenai/search/__init__.py")
    search_client   = filemd5("${path.module}/../../src/lcmgo_cagenai/search/client.py")
    search_mappings = filemd5("${path.module}/../../src/lcmgo_cagenai/search/mappings.py")

    # Parser module
    parser_init           = filemd5("${path.module}/../../src/lcmgo_cagenai/parser/__init__.py")
    parser_schema         = filemd5("${path.module}/../../src/lcmgo_cagenai/parser/schema.py")
    parser_cv_parser      = filemd5("${path.module}/../../src/lcmgo_cagenai/parser/cv_parser.py")
    parser_taxonomy       = filemd5("${path.module}/../../src/lcmgo_cagenai/parser/taxonomy_mapper.py")
    parser_db_writer      = filemd5("${path.module}/../../src/lcmgo_cagenai/parser/db_writer.py")
    parser_search_indexer = filemd5("${path.module}/../../src/lcmgo_cagenai/parser/search_indexer.py")
    parser_validators     = filemd5("${path.module}/../../src/lcmgo_cagenai/parser/validators.py")

    # Query module
    query_init       = filemd5("${path.module}/../../src/lcmgo_cagenai/query/__init__.py")
    query_schema     = filemd5("${path.module}/../../src/lcmgo_cagenai/query/schema.py")
    query_translator = filemd5("${path.module}/../../src/lcmgo_cagenai/query/query_translator.py")
    query_sql_gen    = filemd5("${path.module}/../../src/lcmgo_cagenai/query/sql_generator.py")
    query_router     = filemd5("${path.module}/../../src/lcmgo_cagenai/query/query_router.py")

    # Prompts (embedded in code but tracked for rebuilds)
    prompt_cv_parsing = filemd5("${path.module}/../../prompts/cv_parsing/v1.0.0.txt")

    # Manual version bump - increment to force layer rebuild
    # Last updated: 2026-01-20 (Session 36 - added training support)
    layer_version = "38"
  }

  provisioner "local-exec" {
    command = <<-EOT
      $layerDir = "${path.module}/../../lambda/cv_processor/package_layer"
      $pythonDir = "$layerDir/python"

      # Clean up previous build
      if (Test-Path $layerDir) { Remove-Item -Recurse -Force $layerDir }
      New-Item -ItemType Directory -Force -Path $pythonDir | Out-Null

      # Copy source package
      Copy-Item -Recurse "${path.module}/../../src/lcmgo_cagenai" "$pythonDir/"

      # Remove __pycache__ directories (bytecode may be stale or wrong Python version)
      Get-ChildItem -Path "$pythonDir" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

      # Create zip
      $zipPath = "${path.module}/../../lambda/cv_processor/lcmgo_package_layer.zip"
      if (Test-Path $zipPath) { Remove-Item $zipPath }
      Compress-Archive -Path "$layerDir\*" -DestinationPath $zipPath -Force

      Write-Host "Package layer built: $zipPath"
    EOT

    interpreter = ["powershell", "-Command"]
  }
}

resource "aws_lambda_layer_version" "lcmgo_package" {
  filename            = "${path.module}/../../lambda/cv_processor/lcmgo_package_layer.zip"
  layer_name          = "lcmgo-cagenai-prod-lcmgo-package"
  description         = "LCMGoCloud CA GenAI source package"
  compatible_runtimes = ["python3.11", "python3.12"]
  source_code_hash    = filebase64sha256("${path.module}/../../lambda/cv_processor/lcmgo_package_layer.zip")

  depends_on = [null_resource.lcmgo_package_layer_build]

  lifecycle {
    create_before_destroy = true
  }
}

# Data source to always get the latest published layer version
# Use this in Lambda functions to avoid version drift
data "aws_lambda_layer_version" "lcmgo_package_latest" {
  layer_name = "lcmgo-cagenai-prod-lcmgo-package"

  depends_on = [aws_lambda_layer_version.lcmgo_package]
}

# -----------------------------------------------------------------------------
# Tesseract OCR Lambda Layer (pre-built, deployed via AWS CLI)
# -----------------------------------------------------------------------------

data "aws_lambda_layer_version" "tesseract" {
  layer_name = "lcmgo-cagenai-prod-tesseract-ocr"
}

# -----------------------------------------------------------------------------
# Lambda Function
# -----------------------------------------------------------------------------

data "archive_file" "cv_processor" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/cv_processor/handler.py"
  output_path = "${path.module}/../../lambda/cv_processor/cv_processor.zip"
}

resource "aws_lambda_function" "cv_processor" {
  filename         = data.archive_file.cv_processor.output_path
  source_code_hash = data.archive_file.cv_processor.output_base64sha256
  function_name    = "lcmgo-cagenai-prod-cv-processor"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.handler"
  runtime          = "python3.11"
  timeout          = 300 # 5 minutes for OCR processing
  memory_size      = 1024 # Increased for PDF/image processing

  layers = [
    aws_lambda_layer_version.cv_processor.arn,
    data.aws_lambda_layer_version.lcmgo_package_latest.arn,
    data.aws_lambda_layer_version.tesseract.arn,
  ]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      CV_UPLOADS_BUCKET  = aws_s3_bucket.cv_uploads.bucket
      PROCESSED_BUCKET   = aws_s3_bucket.processed_data.bucket
      STATE_TABLE        = aws_dynamodb_table.cv_processing_state.name
      DB_SECRET_ARN      = aws_secretsmanager_secret.db_credentials.arn
      CV_PARSER_FUNCTION = "lcmgo-cagenai-prod-cv-parser"
      AWS_REGION_NAME    = var.aws_region
      # Tesseract OCR configuration
      TESSDATA_PREFIX    = "/opt/tesseract/share/tessdata"
      PATH               = "/opt/bin:/var/task:/var/lang/bin:/usr/local/bin:/usr/bin:/bin"
      LD_LIBRARY_PATH    = "/opt/lib:/var/lang/lib:/lib64:/usr/lib64"
    }
  }

  tags = merge(local.common_tags, {
    Name = "lcmgo-cagenai-prod-cv-processor"
  })
}

# -----------------------------------------------------------------------------
# S3 Trigger
# -----------------------------------------------------------------------------

resource "aws_lambda_permission" "s3_cv_uploads" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cv_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.cv_uploads.arn
}

resource "aws_s3_bucket_notification" "cv_uploads" {
  bucket = aws_s3_bucket.cv_uploads.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.cv_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".pdf"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.cv_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".docx"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.cv_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".jpg"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.cv_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".jpeg"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.cv_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".png"
  }

  depends_on = [aws_lambda_permission.s3_cv_uploads]
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "cv_processor" {
  name              = "/aws/lambda/lcmgo-cagenai-prod-cv-processor"
  retention_in_days = 30

  tags = merge(local.common_tags, {
    Name = "lcmgo-cagenai-prod-cv-processor-logs"
  })
}

# -----------------------------------------------------------------------------
# IAM Policy for CV Processor specific permissions
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy" "cv_processor_s3" {
  name = "lcmgo-cagenai-prod-cv-processor-s3"
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
        Resource = "${aws_s3_bucket.cv_uploads.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "${aws_s3_bucket.processed_data.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "cv_processor_dynamodb" {
  name = "lcmgo-cagenai-prod-cv-processor-dynamodb"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.cv_processing_state.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "cv_processor_textract" {
  name = "lcmgo-cagenai-prod-cv-processor-textract"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "textract:DetectDocumentText",
          "textract:AnalyzeDocument"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "cv_processor_bedrock" {
  name = "lcmgo-cagenai-prod-cv-processor-bedrock"
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
          "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-*",
          "arn:aws:bedrock:*::foundation-model/cohere.embed-*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "cv_processor_lambda_arn" {
  description = "ARN of the CV processor Lambda function"
  value       = aws_lambda_function.cv_processor.arn
}

output "cv_processor_lambda_name" {
  description = "Name of the CV processor Lambda function"
  value       = aws_lambda_function.cv_processor.function_name
}

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
  }

  provisioner "local-exec" {
    command = <<-EOT
      $layerDir = "${path.module}/../../lambda/cv_processor/layer"
      $pythonDir = "$layerDir/python"

      # Clean up previous build
      if (Test-Path $layerDir) { Remove-Item -Recurse -Force $layerDir }
      New-Item -ItemType Directory -Force -Path $pythonDir | Out-Null

      # Install dependencies
      pip install python-docx pdfplumber Pillow -t $pythonDir --quiet --no-cache-dir

      # Create zip
      $zipPath = "${path.module}/../../lambda/cv_processor/cv_processor_layer.zip"
      if (Test-Path $zipPath) { Remove-Item $zipPath }
      Compress-Archive -Path "$layerDir\*" -DestinationPath $zipPath -Force

      Write-Host "Layer built: $zipPath"
    EOT

    interpreter = ["powershell", "-Command"]
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
    ocr_hash = filemd5("${path.module}/../../src/lcmgo_cagenai/ocr/__init__.py")
    llm_hash = filemd5("${path.module}/../../src/lcmgo_cagenai/llm/provider.py")
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

  depends_on = [null_resource.lcmgo_package_layer_build]

  lifecycle {
    create_before_destroy = true
  }
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
    aws_lambda_layer_version.lcmgo_package.arn,
    data.aws_lambda_layer_version.tesseract.arn,
  ]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      CV_UPLOADS_BUCKET = aws_s3_bucket.cv_uploads.bucket
      PROCESSED_BUCKET  = aws_s3_bucket.processed_data.bucket
      STATE_TABLE       = aws_dynamodb_table.cv_processing_state.name
      DB_SECRET_ARN     = aws_secretsmanager_secret.db_credentials.arn
      AWS_REGION_NAME   = var.aws_region
      # Tesseract OCR configuration
      TESSDATA_PREFIX   = "/opt/tesseract/share/tessdata"
      PATH              = "/opt/bin:/var/task:/var/lang/bin:/usr/local/bin:/usr/bin:/bin"
      LD_LIBRARY_PATH   = "/opt/lib:/var/lang/lib:/lib64:/usr/lib64"
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
          "arn:aws:bedrock:eu-north-1::foundation-model/eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
          "arn:aws:bedrock:eu-north-1::foundation-model/eu.anthropic.claude-haiku-4-5-20251001-v1:0",
          "arn:aws:bedrock:eu-north-1::foundation-model/eu.cohere.embed-v4:0"
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

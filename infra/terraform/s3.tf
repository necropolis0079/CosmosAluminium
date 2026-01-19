# =============================================================================
# LCMGoCloud-CAGenAI - S3 Buckets
# =============================================================================

# -----------------------------------------------------------------------------
# S3 Bucket - CV Uploads (raw files)
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "cv_uploads" {
  bucket        = "${local.name_prefix}-cv-uploads-${local.region_short}"
  force_destroy = var.s3_force_destroy

  tags = {
    Name    = "${local.name_prefix}-cv-uploads-${local.region_short}"
    Purpose = "CV raw file uploads"
  }
}

resource "aws_s3_bucket_versioning" "cv_uploads" {
  bucket = aws_s3_bucket.cv_uploads.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cv_uploads" {
  bucket = aws_s3_bucket.cv_uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "cv_uploads" {
  bucket = aws_s3_bucket.cv_uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS configuration for browser uploads (Testing UI)
resource "aws_s3_bucket_cors_configuration" "cv_uploads" {
  bucket = aws_s3_bucket.cv_uploads.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "POST", "PUT"]
    allowed_origins = [
      "http://localhost:3000",
      "http://localhost:8000",
      "http://127.0.0.1:3000"
    ]
    expose_headers  = ["ETag", "x-amz-meta-correlation-id"]
    max_age_seconds = 3600
  }
}

# Lifecycle rule - move to Glacier after 90 days
resource "aws_s3_bucket_lifecycle_configuration" "cv_uploads" {
  bucket = aws_s3_bucket.cv_uploads.id

  rule {
    id     = "archive-old-cvs"
    status = "Enabled"

    filter {} # Apply to all objects

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555 # ~7 years (GDPR retention)
    }
  }
}

# -----------------------------------------------------------------------------
# S3 Bucket - Processed Data (extracted text, parsed JSON)
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "processed_data" {
  bucket        = "${local.name_prefix}-processed-${local.region_short}"
  force_destroy = var.s3_force_destroy

  tags = {
    Name    = "${local.name_prefix}-processed-${local.region_short}"
    Purpose = "Processed CV data"
  }
}

resource "aws_s3_bucket_versioning" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "processed_data" {
  bucket = aws_s3_bucket.processed_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# S3 Bucket - Lambda Code Artifacts
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "lambda_artifacts" {
  bucket        = "${local.name_prefix}-lambda-artifacts-${local.region_short}"
  force_destroy = var.s3_force_destroy

  tags = {
    Name    = "${local.name_prefix}-lambda-artifacts-${local.region_short}"
    Purpose = "Lambda deployment packages"
  }
}

resource "aws_s3_bucket_versioning" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rule - delete old versions after 30 days
resource "aws_s3_bucket_lifecycle_configuration" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    filter {} # Apply to all objects

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# -----------------------------------------------------------------------------
# S3 Bucket - Terraform State (for remote backend)
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "tfstate" {
  bucket        = "${local.name_prefix}-tfstate-${local.region_short}"
  force_destroy = false # Never auto-delete state bucket

  tags = {
    Name    = "${local.name_prefix}-tfstate-${local.region_short}"
    Purpose = "Terraform state storage"
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# DynamoDB Table for Terraform State Locking
# -----------------------------------------------------------------------------

resource "aws_dynamodb_table" "tfstate_lock" {
  name         = "${local.name_prefix}-tfstate-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name    = "${local.name_prefix}-tfstate-lock"
    Purpose = "Terraform state locking"
  }
}

# -----------------------------------------------------------------------------
# S3 Bucket Notifications (for CV upload triggers)
# Note: Lambda trigger configuration will be added when Lambda is created
# -----------------------------------------------------------------------------

# This will be configured in Phase 4 when Lambda functions are created

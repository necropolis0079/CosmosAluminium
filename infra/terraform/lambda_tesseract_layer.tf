# =============================================================================
# Tesseract OCR Lambda Layer
# =============================================================================
# This layer provides Tesseract OCR binaries for Lambda functions.
# The layer must be built separately using Docker (see lambda/layers/tesseract/)
#
# To enable:
# 1. Build the layer: cd lambda/layers/tesseract && ./build.sh
# 2. Set var.enable_tesseract_layer = true
# 3. Run terraform apply
# =============================================================================

variable "enable_tesseract_layer" {
  description = "Enable Tesseract OCR Lambda layer (requires pre-built layer zip)"
  type        = bool
  default     = false
}

# Upload Tesseract layer zip to S3 (only if enabled)
resource "aws_s3_object" "tesseract_layer" {
  count  = var.enable_tesseract_layer ? 1 : 0
  bucket = aws_s3_bucket.lambda_artifacts.id
  key    = "layers/tesseract-layer.zip"
  source = "${path.module}/../../lambda/layers/tesseract/tesseract-layer.zip"
  etag   = filemd5("${path.module}/../../lambda/layers/tesseract/tesseract-layer.zip")

  tags = {
    Name        = "${local.name_prefix}-tesseract-layer"
    CreatedDate = formatdate("YYYY-MM-DD", timestamp())
  }
}

# Create Lambda layer (only if enabled)
resource "aws_lambda_layer_version" "tesseract" {
  count               = var.enable_tesseract_layer ? 1 : 0
  layer_name          = "${local.name_prefix}-tesseract-ocr"
  description         = "Tesseract OCR 5.3.4 with Greek (ell) and English (eng) language support"
  s3_bucket           = aws_s3_bucket.lambda_artifacts.id
  s3_key              = aws_s3_object.tesseract_layer[0].key
  source_code_hash    = filebase64sha256("${path.module}/../../lambda/layers/tesseract/tesseract-layer.zip")
  compatible_runtimes = ["python3.11", "python3.12"]

  depends_on = [aws_s3_object.tesseract_layer]
}

# Output the layer ARN
output "tesseract_layer_arn" {
  description = "ARN of the Tesseract Lambda layer"
  value       = var.enable_tesseract_layer ? aws_lambda_layer_version.tesseract[0].arn : "Layer not enabled"
}

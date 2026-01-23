# =============================================================================
# LCMGoCloud-CAGenAI - CloudFront Distribution for CV Uploads
# =============================================================================
# Provides secure access to CV files via CloudFront with Origin Access Control
# Benefits: DDoS protection, edge caching, HTTPS enforcement, geo-restriction
#
# Created: 2026-01-23
# =============================================================================

# -----------------------------------------------------------------------------
# Origin Access Control (OAC) - Modern way to secure S3 access from CloudFront
# -----------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_control" "cv_uploads" {
  name                              = "${local.name_prefix}-cv-uploads-oac"
  description                       = "OAC for CV uploads S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# -----------------------------------------------------------------------------
# Custom Cache Policy - Forward All Query Strings for S3 Presigned URLs
# -----------------------------------------------------------------------------
# IMPORTANT: S3 presigned URLs use query string parameters for authentication:
# - X-Amz-Algorithm, X-Amz-Credential, X-Amz-Date, X-Amz-Expires, X-Amz-Signature, etc.
# The default CachingOptimized policy does NOT forward query strings which breaks presigned URLs.

resource "aws_cloudfront_cache_policy" "s3_presigned" {
  name        = "${local.name_prefix}-s3-presigned-policy"
  comment     = "Cache policy for S3 presigned URLs - forwards all query strings"
  default_ttl = 0       # Don't cache by default (presigned URLs are unique)
  max_ttl     = 3600    # Max 1 hour (matches presigned URL expiry)
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "all"  # Forward ALL query strings for presigned URL auth
    }
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
  }
}

# -----------------------------------------------------------------------------
# CloudFront Distribution
# -----------------------------------------------------------------------------

resource "aws_cloudfront_distribution" "cv_uploads" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "CV uploads distribution - ${local.name_prefix}"
  default_root_object = ""
  price_class         = "PriceClass_100"  # US, Canada, Europe only (cost optimization)

  # S3 Origin with OAC
  origin {
    domain_name              = aws_s3_bucket.cv_uploads.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.cv_uploads.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.cv_uploads.id
  }

  # Default cache behavior
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.cv_uploads.id}"

    # Use custom cache policy that forwards query strings for presigned URLs
    cache_policy_id          = aws_cloudfront_cache_policy.s3_presigned.id
    origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"  # CORS-S3Origin

    viewer_protocol_policy = "https-only"
    compress               = true
  }

  # Geo-restriction (EU only for GDPR compliance)
  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["GR", "DE", "FR", "IT", "ES", "NL", "BE", "AT", "PT", "SE", "FI", "DK", "IE", "PL", "CZ", "HU", "RO", "BG", "HR", "SK", "SI", "LT", "LV", "EE", "CY", "MT", "LU", "GB", "CH", "NO"]
    }
  }

  # Use default CloudFront certificate
  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-cv-uploads-cdn"
    Purpose = "CV file distribution"
  })
}

# -----------------------------------------------------------------------------
# S3 Bucket Policy - Allow CloudFront OAC Access
# -----------------------------------------------------------------------------

resource "aws_s3_bucket_policy" "cv_uploads_cloudfront" {
  bucket = aws_s3_bucket.cv_uploads.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontOAC"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.cv_uploads.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.cv_uploads.arn
          }
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for CV uploads"
  value       = aws_cloudfront_distribution.cv_uploads.id
}

output "cloudfront_domain_name" {
  description = "CloudFront domain name for CV uploads"
  value       = aws_cloudfront_distribution.cv_uploads.domain_name
}

output "cloudfront_url" {
  description = "CloudFront URL for CV uploads"
  value       = "https://${aws_cloudfront_distribution.cv_uploads.domain_name}"
}

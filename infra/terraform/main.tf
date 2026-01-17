# =============================================================================
# LCMGoCloud-CAGenAI - Terraform Main Configuration
# =============================================================================
# AWS Region: eu-north-1 (Stockholm)
# Environment: Production
# =============================================================================

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Backend configuration for state management (S3 with native locking)
  backend "s3" {
    bucket       = "lcmgo-cagenai-prod-tfstate-eun1"
    key          = "terraform.tfstate"
    region       = "eu-north-1"
    encrypt      = true
    use_lockfile = true
  }
}

# -----------------------------------------------------------------------------
# AWS Provider Configuration
# -----------------------------------------------------------------------------

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      Owner       = "LCMGoCloud"
      CostCenter  = "CA-GenAI"
      ManagedBy   = "terraform"
    }
  }
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

# -----------------------------------------------------------------------------
# Local Values
# -----------------------------------------------------------------------------

locals {
  # Naming prefix for all resources
  name_prefix = "${var.project_short_name}-${var.environment}"

  # Region short code for resource naming
  region_short = "eun1"

  # Common tags (merged with provider default_tags)
  common_tags = {
    CreatedDate = formatdate("YYYY-MM-DD", timestamp())
  }

  # Availability zones to use
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

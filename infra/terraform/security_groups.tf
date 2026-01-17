# =============================================================================
# LCMGoCloud-CAGenAI - Security Groups
# =============================================================================

# -----------------------------------------------------------------------------
# Security Group - Lambda Functions
# -----------------------------------------------------------------------------

resource "aws_security_group" "lambda" {
  name        = "${local.name_prefix}-sg-lambda"
  description = "Security group for Lambda functions"
  vpc_id      = aws_vpc.main.id

  # Lambda needs outbound access to:
  # - RDS PostgreSQL
  # - OpenSearch
  # - AWS services (Bedrock, S3, DynamoDB, etc.)
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-sg-lambda"
  }
}

# -----------------------------------------------------------------------------
# Security Group - RDS PostgreSQL
# -----------------------------------------------------------------------------

resource "aws_security_group" "rds" {
  name        = "${local.name_prefix}-sg-db"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  # Allow PostgreSQL from Lambda
  ingress {
    description     = "PostgreSQL from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  # No outbound rules - database doesn't need to initiate connections
  egress {
    description = "Allow outbound to VPC (for updates/patches if needed)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${local.name_prefix}-sg-db"
  }
}

# -----------------------------------------------------------------------------
# Security Group - OpenSearch
# -----------------------------------------------------------------------------

resource "aws_security_group" "opensearch" {
  name        = "${local.name_prefix}-sg-opensearch"
  description = "Security group for OpenSearch domain"
  vpc_id      = aws_vpc.main.id

  # Allow HTTPS from Lambda
  ingress {
    description     = "HTTPS from Lambda"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  egress {
    description = "Allow outbound to VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${local.name_prefix}-sg-opensearch"
  }
}

# -----------------------------------------------------------------------------
# Security Group - ALB (Application Load Balancer)
# -----------------------------------------------------------------------------

resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-sg-alb"
  description = "Security group for Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  # Allow HTTPS from internet
  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow HTTP (redirect to HTTPS)
  ingress {
    description = "HTTP from anywhere (redirect to HTTPS)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow outbound to VPC (for health checks and Lambda)
  egress {
    description = "Allow outbound to VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${local.name_prefix}-sg-alb"
  }
}

# -----------------------------------------------------------------------------
# Security Group - VPC Endpoints (Interface Endpoints)
# -----------------------------------------------------------------------------

resource "aws_security_group" "vpc_endpoints" {
  name        = "${local.name_prefix}-sg-vpce"
  description = "Security group for VPC Interface Endpoints"
  vpc_id      = aws_vpc.main.id

  # Allow HTTPS from VPC
  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-sg-vpce"
  }
}

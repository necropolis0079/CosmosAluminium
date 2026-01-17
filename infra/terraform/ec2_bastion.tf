# =============================================================================
# LCMGoCloud-CAGenAI - Bastion Host EC2
# =============================================================================
# Purpose: SSH access to VPC resources (RDS PostgreSQL, OpenSearch)
# Instance: t3.small in public subnet with public IP
# =============================================================================

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

variable "bastion_allowed_ip" {
  description = "Your public IP address for SSH access"
  type        = string
  default     = "31.217.175.79/32"
}

# -----------------------------------------------------------------------------
# Data Source - Latest Amazon Linux 2023 AMI
# -----------------------------------------------------------------------------

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# -----------------------------------------------------------------------------
# SSH Key Pair
# -----------------------------------------------------------------------------

resource "tls_private_key" "bastion" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "bastion" {
  key_name   = "${local.name_prefix}-bastion-key"
  public_key = tls_private_key.bastion.public_key_openssh

  tags = {
    Name = "${local.name_prefix}-bastion-key"
  }
}

# Store private key in Secrets Manager for retrieval
resource "aws_secretsmanager_secret" "bastion_ssh_key" {
  name        = "${local.name_prefix}-bastion-ssh-key"
  description = "SSH private key for bastion host"

  tags = {
    Name = "${local.name_prefix}-bastion-ssh-key"
  }
}

resource "aws_secretsmanager_secret_version" "bastion_ssh_key" {
  secret_id     = aws_secretsmanager_secret.bastion_ssh_key.id
  secret_string = tls_private_key.bastion.private_key_pem
}

# -----------------------------------------------------------------------------
# Security Group - Bastion Host
# -----------------------------------------------------------------------------

resource "aws_security_group" "bastion" {
  name        = "${local.name_prefix}-sg-bastion"
  description = "Security group for Bastion host - SSH access"
  vpc_id      = aws_vpc.main.id

  # Allow SSH from user's IP
  ingress {
    description = "SSH from allowed IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.bastion_allowed_ip]
  }

  # Allow all outbound traffic (for package updates, database connections, etc.)
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-sg-bastion"
  }
}

# -----------------------------------------------------------------------------
# Add Bastion access to RDS Security Group
# -----------------------------------------------------------------------------

resource "aws_security_group_rule" "rds_from_bastion" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.bastion.id
  description              = "PostgreSQL from Bastion"
}

# -----------------------------------------------------------------------------
# Add Bastion access to OpenSearch Security Group
# -----------------------------------------------------------------------------

resource "aws_security_group_rule" "opensearch_from_bastion" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.opensearch.id
  source_security_group_id = aws_security_group.bastion.id
  description              = "HTTPS from Bastion"
}

# -----------------------------------------------------------------------------
# IAM Role for Bastion (for SSM Session Manager fallback)
# -----------------------------------------------------------------------------

resource "aws_iam_role" "bastion" {
  name = "${local.name_prefix}-bastion-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-bastion-role"
  }
}

resource "aws_iam_role_policy_attachment" "bastion_ssm" {
  role       = aws_iam_role.bastion.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "bastion" {
  name = "${local.name_prefix}-bastion-profile"
  role = aws_iam_role.bastion.name

  tags = {
    Name = "${local.name_prefix}-bastion-profile"
  }
}

# -----------------------------------------------------------------------------
# EC2 Instance - Bastion Host
# -----------------------------------------------------------------------------

resource "aws_instance" "bastion" {
  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = "t3.small"
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.bastion.id]
  key_name                    = aws_key_pair.bastion.key_name
  iam_instance_profile        = aws_iam_instance_profile.bastion.name
  associate_public_ip_address = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30
    encrypted             = true
    delete_on_termination = true
  }

  # Install useful tools via user_data
  user_data = <<-EOF
    #!/bin/bash
    dnf update -y
    dnf install -y postgresql15 python3.11 python3.11-pip jq curl htop
    pip3.11 install awscli boto3 opensearch-py requests-aws4auth pg8000

    # Create connection helper scripts
    cat > /home/ec2-user/connect_postgres.sh << 'SCRIPT'
    #!/bin/bash
    # Get credentials from Secrets Manager
    SECRET=$(aws secretsmanager get-secret-value --secret-id lcmgo-cagenai-prod-db-credentials --region eu-north-1 --query SecretString --output text)
    DB_HOST=$(echo $SECRET | jq -r '.host')
    DB_USER=$(echo $SECRET | jq -r '.username')
    DB_PASS=$(echo $SECRET | jq -r '.password')
    DB_NAME=$(echo $SECRET | jq -r '.dbname // "cagenai"')

    PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME
    SCRIPT
    chmod +x /home/ec2-user/connect_postgres.sh
    chown ec2-user:ec2-user /home/ec2-user/connect_postgres.sh

    cat > /home/ec2-user/test_opensearch.sh << 'SCRIPT'
    #!/bin/bash
    ENDPOINT="https://vpc-lcmgo-cagenai-prod-search-zg67rx23eou363nwlybpkkmlea.eu-north-1.es.amazonaws.com"
    curl -s "$ENDPOINT/_cat/indices?v"
    SCRIPT
    chmod +x /home/ec2-user/test_opensearch.sh
    chown ec2-user:ec2-user /home/ec2-user/test_opensearch.sh

    echo "Bastion setup complete" > /home/ec2-user/setup_complete.txt
  EOF

  tags = {
    Name = "${local.name_prefix}-bastion"
  }

  lifecycle {
    ignore_changes = [ami]  # Don't replace on AMI updates
  }
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "bastion_public_ip" {
  description = "Public IP of the bastion host"
  value       = aws_instance.bastion.public_ip
}

output "bastion_public_dns" {
  description = "Public DNS of the bastion host"
  value       = aws_instance.bastion.public_dns
}

output "bastion_instance_id" {
  description = "Instance ID of the bastion host"
  value       = aws_instance.bastion.id
}

output "bastion_ssh_key_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the SSH private key"
  value       = aws_secretsmanager_secret.bastion_ssh_key.arn
}

output "bastion_ssh_command" {
  description = "SSH command to connect to bastion (after retrieving key)"
  value       = "ssh -i bastion-key.pem ec2-user@${aws_instance.bastion.public_ip}"
}

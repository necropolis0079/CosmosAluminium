# Terraform Infrastructure - LCMGoCloud-CAGenAI

This directory contains Terraform configuration for the LCMGoCloud-CAGenAI AWS infrastructure.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads.html) >= 1.6.0
- AWS CLI configured with appropriate credentials
- AWS account with permissions to create VPC, S3, IAM, etc.

## Quick Start

1. **Copy the example variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit terraform.tfvars with your values:**
   - Set `db_password` to a secure password
   - Adjust other values as needed

3. **Initialize Terraform:**
   ```bash
   terraform init
   ```

4. **Review the plan:**
   ```bash
   terraform plan
   ```

5. **Apply the configuration:**
   ```bash
   terraform apply
   ```

## Files

| File | Description |
|------|-------------|
| `main.tf` | Provider configuration, locals, data sources |
| `variables.tf` | Variable definitions |
| `vpc.tf` | VPC, subnets, route tables, NAT gateway |
| `security_groups.tf` | Security groups for Lambda, RDS, OpenSearch, ALB |
| `iam.tf` | IAM roles and policies for Lambda |
| `s3.tf` | S3 buckets for CV uploads, processed data, artifacts |
| `outputs.tf` | Output values (VPC ID, subnet IDs, etc.) |
| `terraform.tfvars.example` | Example variables file |

## Architecture

```
VPC: 10.10.0.0/20 (eu-north-1)
├── Public Subnets (10.10.0-2.0/24) - ALB, NAT Gateway
├── Private Subnets (10.10.4-8.0/23) - Lambda, Application
└── Database Subnets (10.10.10-11.0/25) - RDS, OpenSearch
```

## Phase 1 Resources Created

- VPC with DNS hostnames enabled
- 3 public subnets (one per AZ)
- 3 private subnets (one per AZ)
- 3 database subnets (one per AZ)
- Internet Gateway
- NAT Gateway (single, for cost optimization)
- Route tables (public + private)
- Security groups (Lambda, RDS, OpenSearch, ALB, VPC endpoints)
- IAM role for Lambda with policies for S3, DynamoDB, Bedrock, Textract, etc.
- S3 buckets (CV uploads, processed data, Lambda artifacts, Terraform state)
- DynamoDB table for Terraform state locking
- VPC endpoints for S3 and DynamoDB (free, reduces NAT costs)

## Remote State (Optional)

After initial apply, you can enable remote state:

1. Uncomment the backend configuration in `main.tf`
2. Run `terraform init -migrate-state`

## Next Steps (Phase 2)

- RDS PostgreSQL instance
- OpenSearch domain
- DynamoDB tables for state machine

## Cost Optimization

- Single NAT Gateway (~$32/month)
- VPC endpoints for S3/DynamoDB (free, avoids NAT charges)
- Single-AZ RDS (disabled Multi-AZ)
- Single OpenSearch node

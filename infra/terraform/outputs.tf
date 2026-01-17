# =============================================================================
# LCMGoCloud-CAGenAI - Terraform Outputs
# =============================================================================

# -----------------------------------------------------------------------------
# VPC Outputs
# -----------------------------------------------------------------------------

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "IDs of database subnets"
  value       = aws_subnet.database[*].id
}

output "db_subnet_group_name" {
  description = "Name of the RDS subnet group"
  value       = aws_db_subnet_group.main.name
}

# -----------------------------------------------------------------------------
# Security Group Outputs
# -----------------------------------------------------------------------------

output "security_group_lambda_id" {
  description = "ID of the Lambda security group"
  value       = aws_security_group.lambda.id
}

output "security_group_rds_id" {
  description = "ID of the RDS security group"
  value       = aws_security_group.rds.id
}

output "security_group_opensearch_id" {
  description = "ID of the OpenSearch security group"
  value       = aws_security_group.opensearch.id
}

output "security_group_alb_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

# -----------------------------------------------------------------------------
# IAM Outputs
# -----------------------------------------------------------------------------

output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "lambda_execution_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.name
}

# -----------------------------------------------------------------------------
# S3 Outputs
# -----------------------------------------------------------------------------

output "s3_bucket_cv_uploads" {
  description = "Name of the CV uploads S3 bucket"
  value       = aws_s3_bucket.cv_uploads.id
}

output "s3_bucket_cv_uploads_arn" {
  description = "ARN of the CV uploads S3 bucket"
  value       = aws_s3_bucket.cv_uploads.arn
}

output "s3_bucket_processed_data" {
  description = "Name of the processed data S3 bucket"
  value       = aws_s3_bucket.processed_data.id
}

output "s3_bucket_processed_data_arn" {
  description = "ARN of the processed data S3 bucket"
  value       = aws_s3_bucket.processed_data.arn
}

output "s3_bucket_lambda_artifacts" {
  description = "Name of the Lambda artifacts S3 bucket"
  value       = aws_s3_bucket.lambda_artifacts.id
}

output "s3_bucket_tfstate" {
  description = "Name of the Terraform state S3 bucket"
  value       = aws_s3_bucket.tfstate.id
}

# -----------------------------------------------------------------------------
# VPC Endpoint Outputs
# -----------------------------------------------------------------------------

output "vpc_endpoint_s3_id" {
  description = "ID of the S3 VPC endpoint"
  value       = aws_vpc_endpoint.s3.id
}

output "vpc_endpoint_dynamodb_id" {
  description = "ID of the DynamoDB VPC endpoint"
  value       = aws_vpc_endpoint.dynamodb.id
}

# -----------------------------------------------------------------------------
# Network Outputs
# -----------------------------------------------------------------------------

output "nat_gateway_ids" {
  description = "IDs of NAT Gateways"
  value       = aws_nat_gateway.main[*].id
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

# -----------------------------------------------------------------------------
# DynamoDB Outputs
# -----------------------------------------------------------------------------

output "dynamodb_tfstate_lock_table" {
  description = "Name of the Terraform state lock DynamoDB table"
  value       = aws_dynamodb_table.tfstate_lock.name
}

# -----------------------------------------------------------------------------
# AWS Account Info
# -----------------------------------------------------------------------------

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS Region"
  value       = data.aws_region.current.name
}

# -----------------------------------------------------------------------------
# Cognito Outputs
# -----------------------------------------------------------------------------

output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_arn" {
  description = "ARN of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.arn
}

output "cognito_user_pool_domain" {
  description = "Domain of the Cognito User Pool"
  value       = aws_cognito_user_pool_domain.main.domain
}

output "cognito_user_pool_endpoint" {
  description = "Endpoint of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.endpoint
}

output "cognito_web_client_id" {
  description = "ID of the Cognito Web App Client"
  value       = aws_cognito_user_pool_client.web.id
}

output "cognito_api_client_id" {
  description = "ID of the Cognito API Client"
  value       = aws_cognito_user_pool_client.api.id
}

output "cognito_user_groups" {
  description = "Cognito User Groups"
  value = {
    super_admin = aws_cognito_user_group.super_admin.name
    admins      = aws_cognito_user_group.admins.name
    hr_users    = aws_cognito_user_group.hr_users.name
  }
}

# -----------------------------------------------------------------------------
# RDS Outputs
# -----------------------------------------------------------------------------

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.main.endpoint
}

output "rds_address" {
  description = "RDS PostgreSQL address (hostname only)"
  value       = aws_db_instance.main.address
}

output "rds_port" {
  description = "RDS PostgreSQL port"
  value       = aws_db_instance.main.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "rds_identifier" {
  description = "RDS instance identifier"
  value       = aws_db_instance.main.identifier
}

output "rds_credentials_secret_arn" {
  description = "ARN of the Secrets Manager secret containing DB credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

# -----------------------------------------------------------------------------
# OpenSearch Outputs
# -----------------------------------------------------------------------------

output "opensearch_endpoint" {
  description = "OpenSearch domain endpoint"
  value       = aws_opensearch_domain.main.endpoint
}

output "opensearch_domain_name" {
  description = "OpenSearch domain name"
  value       = aws_opensearch_domain.main.domain_name
}

output "opensearch_domain_arn" {
  description = "OpenSearch domain ARN"
  value       = aws_opensearch_domain.main.arn
}

output "opensearch_kibana_endpoint" {
  description = "OpenSearch Dashboards endpoint"
  value       = aws_opensearch_domain.main.dashboard_endpoint
}

# -----------------------------------------------------------------------------
# DynamoDB Outputs
# -----------------------------------------------------------------------------

output "dynamodb_cv_processing_state_table" {
  description = "DynamoDB CV processing state table name"
  value       = aws_dynamodb_table.cv_processing_state.name
}

output "dynamodb_cv_processing_state_arn" {
  description = "DynamoDB CV processing state table ARN"
  value       = aws_dynamodb_table.cv_processing_state.arn
}

output "dynamodb_query_cache_table" {
  description = "DynamoDB query cache table name"
  value       = aws_dynamodb_table.query_cache.name
}

output "dynamodb_user_sessions_table" {
  description = "DynamoDB user sessions table name"
  value       = aws_dynamodb_table.user_sessions.name
}

output "dynamodb_prompt_versions_table" {
  description = "DynamoDB prompt versions table name"
  value       = aws_dynamodb_table.prompt_versions.name
}

# -----------------------------------------------------------------------------
# API Gateway Outputs
# -----------------------------------------------------------------------------

output "api_gateway_id" {
  description = "ID of the HTTP API Gateway"
  value       = aws_apigatewayv2_api.main.id
}

output "api_gateway_endpoint" {
  description = "Invoke URL for the API Gateway (v1 stage)"
  value       = aws_apigatewayv2_stage.v1.invoke_url
}

output "api_gateway_arn" {
  description = "ARN of the HTTP API Gateway"
  value       = aws_apigatewayv2_api.main.arn
}

output "api_gateway_execution_arn" {
  description = "Execution ARN of the HTTP API Gateway"
  value       = aws_apigatewayv2_api.main.execution_arn
}

output "health_lambda_arn" {
  description = "ARN of the Health Lambda function"
  value       = aws_lambda_function.health.arn
}

output "health_lambda_name" {
  description = "Name of the Health Lambda function"
  value       = aws_lambda_function.health.function_name
}

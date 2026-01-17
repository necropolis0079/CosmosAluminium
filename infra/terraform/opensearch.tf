# =============================================================================
# LCMGoCloud-CAGenAI - OpenSearch Service (Vector Database)
# =============================================================================
# OpenSearch 2.11 with k-NN plugin for vector similarity search
# - 1024-dimensional embeddings (Cohere Embed v4)
# - HNSW algorithm with cosine similarity
# - Custom Greek language analyzers
# =============================================================================

# -----------------------------------------------------------------------------
# OpenSearch Service Domain
# -----------------------------------------------------------------------------

resource "aws_opensearch_domain" "main" {
  domain_name    = "${local.name_prefix}-search"
  engine_version = "OpenSearch_2.11"

  # Cluster configuration
  cluster_config {
    instance_type            = var.opensearch_instance_type
    instance_count           = var.opensearch_instance_count
    dedicated_master_enabled = false
    zone_awareness_enabled   = false

    # Warm storage (disabled for cost optimization)
    warm_enabled = false
  }

  # EBS storage
  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = var.opensearch_volume_size
    iops        = 3000
    throughput  = 125
  }

  # VPC configuration
  vpc_options {
    subnet_ids         = [aws_subnet.private[0].id] # Single node, single subnet
    security_group_ids = [aws_security_group.opensearch.id]
  }

  # Encryption
  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  # Domain endpoint options
  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-PFS-2023-10"
  }

  # Access policies
  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda_execution.arn
        }
        Action   = "es:*"
        Resource = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${local.name_prefix}-search/*"
      },
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.bastion.arn
        }
        Action   = "es:*"
        Resource = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${local.name_prefix}-search/*"
      }
    ]
  })

  # Advanced options for k-NN
  advanced_options = {
    "rest.action.multi.allow_explicit_index" = "true"
    "indices.query.bool.max_clause_count"    = "1024"
  }

  # Logging
  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_index_slow.arn
    log_type                 = "INDEX_SLOW_LOGS"
    enabled                  = true
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_search_slow.arn
    log_type                 = "SEARCH_SLOW_LOGS"
    enabled                  = true
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_error.arn
    log_type                 = "ES_APPLICATION_LOGS"
    enabled                  = true
  }

  # Auto-tune (disabled for t3.medium)
  auto_tune_options {
    desired_state       = "DISABLED"
    rollback_on_disable = "NO_ROLLBACK"
  }

  # Software update options
  software_update_options {
    auto_software_update_enabled = true
  }

  tags = {
    Name = "${local.name_prefix}-search"
  }

  depends_on = [
    aws_cloudwatch_log_resource_policy.opensearch
  ]
}

# -----------------------------------------------------------------------------
# CloudWatch Log Groups for OpenSearch
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "opensearch_index_slow" {
  name              = "/aws/opensearch/${local.name_prefix}-search/index-slow-logs"
  retention_in_days = 14

  tags = {
    Name = "${local.name_prefix}-opensearch-index-slow"
  }
}

resource "aws_cloudwatch_log_group" "opensearch_search_slow" {
  name              = "/aws/opensearch/${local.name_prefix}-search/search-slow-logs"
  retention_in_days = 14

  tags = {
    Name = "${local.name_prefix}-opensearch-search-slow"
  }
}

resource "aws_cloudwatch_log_group" "opensearch_error" {
  name              = "/aws/opensearch/${local.name_prefix}-search/error-logs"
  retention_in_days = 30

  tags = {
    Name = "${local.name_prefix}-opensearch-error"
  }
}

# -----------------------------------------------------------------------------
# CloudWatch Log Resource Policy for OpenSearch
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_resource_policy" "opensearch" {
  policy_name = "${local.name_prefix}-opensearch-logs-policy"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "es.amazonaws.com"
        }
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:PutLogEventsBatch"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.opensearch_index_slow.arn}:*",
          "${aws_cloudwatch_log_group.opensearch_search_slow.arn}:*",
          "${aws_cloudwatch_log_group.opensearch_error.arn}:*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms for OpenSearch
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "opensearch_cluster_red" {
  alarm_name          = "${local.name_prefix}-opensearch-cluster-red"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ClusterStatus.red"
  namespace           = "AWS/ES"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "OpenSearch cluster status is RED"

  dimensions = {
    DomainName = aws_opensearch_domain.main.domain_name
    ClientId   = data.aws_caller_identity.current.account_id
  }

  tags = {
    Name = "${local.name_prefix}-opensearch-cluster-red"
  }
}

resource "aws_cloudwatch_metric_alarm" "opensearch_cluster_yellow" {
  alarm_name          = "${local.name_prefix}-opensearch-cluster-yellow"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 5
  metric_name         = "ClusterStatus.yellow"
  namespace           = "AWS/ES"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "OpenSearch cluster status is YELLOW for 5 minutes"

  dimensions = {
    DomainName = aws_opensearch_domain.main.domain_name
    ClientId   = data.aws_caller_identity.current.account_id
  }

  tags = {
    Name = "${local.name_prefix}-opensearch-cluster-yellow"
  }
}

resource "aws_cloudwatch_metric_alarm" "opensearch_storage" {
  alarm_name          = "${local.name_prefix}-opensearch-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/ES"
  period              = 300
  statistic           = "Minimum"
  threshold           = 3000 # 3 GB in MB
  alarm_description   = "OpenSearch free storage below 3GB"

  dimensions = {
    DomainName = aws_opensearch_domain.main.domain_name
    ClientId   = data.aws_caller_identity.current.account_id
  }

  tags = {
    Name = "${local.name_prefix}-opensearch-low-storage"
  }
}

resource "aws_cloudwatch_metric_alarm" "opensearch_cpu" {
  alarm_name          = "${local.name_prefix}-opensearch-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ES"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "OpenSearch CPU utilization exceeds 80%"

  dimensions = {
    DomainName = aws_opensearch_domain.main.domain_name
    ClientId   = data.aws_caller_identity.current.account_id
  }

  tags = {
    Name = "${local.name_prefix}-opensearch-high-cpu"
  }
}

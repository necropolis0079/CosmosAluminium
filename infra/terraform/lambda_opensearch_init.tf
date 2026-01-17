# =============================================================================
# OpenSearch Index Initialization Lambda
# =============================================================================
# Creates OpenSearch indices with k-NN mappings for vector search:
# - cosmos-hr-candidates: CV embeddings and candidate data
# - cosmos-hr-jobs: Job postings with requirements
# =============================================================================

# -----------------------------------------------------------------------------
# Lambda Layer for OpenSearch dependencies
# -----------------------------------------------------------------------------

resource "null_resource" "opensearch_layer_build" {
  triggers = {
    requirements_hash = filemd5("${path.module}/../../lambda/opensearch_init/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      $layerDir = "${path.module}/../../lambda/opensearch_init/layer"
      $pythonDir = "$layerDir/python"

      # Clean up previous build
      if (Test-Path $layerDir) { Remove-Item -Recurse -Force $layerDir }
      New-Item -ItemType Directory -Force -Path $pythonDir | Out-Null

      # Install dependencies
      pip install opensearch-py requests-aws4auth -t $pythonDir --quiet --no-cache-dir

      # Create zip
      $zipPath = "${path.module}/../../lambda/opensearch_init/opensearch_layer.zip"
      if (Test-Path $zipPath) { Remove-Item $zipPath }
      Compress-Archive -Path "$layerDir\*" -DestinationPath $zipPath -Force

      Write-Host "Layer built: $zipPath"
    EOT

    interpreter = ["powershell", "-Command"]
  }
}

resource "aws_lambda_layer_version" "opensearch" {
  filename            = "${path.module}/../../lambda/opensearch_init/opensearch_layer.zip"
  layer_name          = "lcmgo-cagenai-prod-opensearch"
  description         = "OpenSearch client dependencies: opensearch-py, requests-aws4auth"
  compatible_runtimes = ["python3.11", "python3.12"]

  depends_on = [null_resource.opensearch_layer_build]

  lifecycle {
    create_before_destroy = true
  }
}

# -----------------------------------------------------------------------------
# Lambda Function
# -----------------------------------------------------------------------------

data "archive_file" "opensearch_init" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/opensearch_init/handler.py"
  output_path = "${path.module}/../../lambda/opensearch_init/opensearch_init.zip"
}

resource "aws_lambda_function" "opensearch_init" {
  filename         = data.archive_file.opensearch_init.output_path
  source_code_hash = data.archive_file.opensearch_init.output_base64sha256
  function_name    = "lcmgo-cagenai-prod-opensearch-init"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 256

  layers = [
    aws_lambda_layer_version.opensearch.arn,
    aws_lambda_layer_version.lcmgo_package.arn,
  ]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      OPENSEARCH_ENDPOINT = aws_opensearch_domain.main.endpoint
      AWS_REGION_NAME     = var.aws_region
    }
  }

  tags = merge(local.common_tags, {
    Name = "lcmgo-cagenai-prod-opensearch-init"
  })

  depends_on = [
    aws_lambda_layer_version.opensearch,
    aws_lambda_layer_version.lcmgo_package,
  ]
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "opensearch_init" {
  name              = "/aws/lambda/lcmgo-cagenai-prod-opensearch-init"
  retention_in_days = 30

  tags = merge(local.common_tags, {
    Name = "lcmgo-cagenai-prod-opensearch-init-logs"
  })
}

# -----------------------------------------------------------------------------
# IAM Policy for OpenSearch access (Lambda already has es:* from opensearch.tf)
# This is just for documentation - the access policy in opensearch.tf grants access
# -----------------------------------------------------------------------------

# Note: The Lambda execution role already has OpenSearch access via the domain's
# access_policies in opensearch.tf. No additional IAM policy needed.

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "opensearch_init_lambda_arn" {
  description = "ARN of the OpenSearch init Lambda function"
  value       = aws_lambda_function.opensearch_init.arn
}

output "opensearch_init_lambda_name" {
  description = "Name of the OpenSearch init Lambda function"
  value       = aws_lambda_function.opensearch_init.function_name
}

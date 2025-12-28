# =============================================================================
# AquaSkill Core v2.0 - AWS Infrastructure (Terraform)
# =============================================================================
# Production infrastructure for Plan-then-Execute LOD 500 pipeline
#
# Resources:
# - S3 Buckets: Plans, Results, Revit Data, NFPA Knowledge Base
# - Lambda: Planner, Executor, Verifier functions
# - Bedrock: Knowledge Base for NFPA 13 RAG
# - IAM: Roles and policies for AgentCore
# - CloudWatch: Logging and audit trail
# - Step Functions: Pipeline orchestration
#
# Usage:
#   terraform init
#   terraform plan -var="environment=dev"
#   terraform apply
#
# Author: AquaBrain V10.0 Platinum
# Date: 2025-12-06
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # S3 backend for state management (uncomment for production)
  # backend "s3" {
  #   bucket         = "aquaskill-terraform-state"
  #   key            = "aquaskill-core/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "aquaskill-terraform-locks"
  #   encrypt        = true
  # }
}

# =============================================================================
# VARIABLES
# =============================================================================

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "aquaskill"
}

variable "nfpa_kb_embedding_model" {
  description = "Bedrock embedding model for NFPA Knowledge Base"
  type        = string
  default     = "amazon.titan-embed-text-v1"
}

variable "foundation_model" {
  description = "Bedrock foundation model for AI operations"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

# =============================================================================
# PROVIDER
# =============================================================================

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AquaSkill"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Version     = "v10.0"
    }
  }
}

# =============================================================================
# DATA SOURCES
# =============================================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# =============================================================================
# S3 BUCKETS
# =============================================================================

# Plans Storage
resource "aws_s3_bucket" "plans" {
  bucket = "${var.project_name}-plans-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name    = "AquaSkill Plans Storage"
    Purpose = "Execution plans from Planner"
  }
}

resource "aws_s3_bucket_versioning" "plans" {
  bucket = aws_s3_bucket.plans.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "plans" {
  bucket = aws_s3_bucket.plans.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Results Storage
resource "aws_s3_bucket" "results" {
  bucket = "${var.project_name}-results-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name    = "AquaSkill Results Storage"
    Purpose = "Verification reports and LOD 500 output"
  }
}

resource "aws_s3_bucket_versioning" "results" {
  bucket = aws_s3_bucket.results.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "results" {
  bucket = aws_s3_bucket.results.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Revit Data Storage (Large files)
resource "aws_s3_bucket" "revit_data" {
  bucket = "${var.project_name}-revit-data-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name    = "AquaSkill Revit Data"
    Purpose = "RVT model geometry and semantic data"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "revit_data" {
  bucket = aws_s3_bucket.revit_data.id

  rule {
    id     = "archive-old-models"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# NFPA Knowledge Base Documents
resource "aws_s3_bucket" "nfpa_docs" {
  bucket = "${var.project_name}-nfpa-docs-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name    = "NFPA 13 Documentation"
    Purpose = "RAG source documents for Knowledge Base"
  }
}

# =============================================================================
# IAM ROLES
# =============================================================================

# Lambda Execution Role
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "${var.project_name}-lambda-s3-access"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.plans.arn,
          "${aws_s3_bucket.plans.arn}/*",
          aws_s3_bucket.results.arn,
          "${aws_s3_bucket.results.arn}/*",
          aws_s3_bucket.revit_data.arn,
          "${aws_s3_bucket.revit_data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_bedrock_access" {
  name = "${var.project_name}-lambda-bedrock-access"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock-agent-runtime:Retrieve",
          "bedrock-agent-runtime:RetrieveAndGenerate"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Step Functions Execution Role
resource "aws_iam_role" "step_functions_exec" {
  name = "${var.project_name}-sfn-exec-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "step_functions_lambda_invoke" {
  name = "${var.project_name}-sfn-lambda-invoke"
  role = aws_iam_role.step_functions_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = [
          aws_lambda_function.planner.arn,
          aws_lambda_function.executor.arn,
          aws_lambda_function.verifier.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

# Bedrock Knowledge Base Role
resource "aws_iam_role" "bedrock_kb" {
  name = "${var.project_name}-bedrock-kb-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "bedrock_kb_s3" {
  name = "${var.project_name}-bedrock-kb-s3"
  role = aws_iam_role.bedrock_kb.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.nfpa_docs.arn,
          "${aws_s3_bucket.nfpa_docs.arn}/*"
        ]
      }
    ]
  })
}

# =============================================================================
# CLOUDWATCH LOG GROUPS
# =============================================================================

resource "aws_cloudwatch_log_group" "planner" {
  name              = "/aws/lambda/${var.project_name}-planner-${var.environment}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "executor" {
  name              = "/aws/lambda/${var.project_name}-executor-${var.environment}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "verifier" {
  name              = "/aws/lambda/${var.project_name}-verifier-${var.environment}"
  retention_in_days = 90  # Keep audit logs longer
}

resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/states/${var.project_name}-pipeline-${var.environment}"
  retention_in_days = 90
}

# =============================================================================
# LAMBDA FUNCTIONS
# =============================================================================

# Lambda Layer for shared dependencies
resource "aws_lambda_layer_version" "aquaskill_common" {
  filename            = "lambda_layers/aquaskill_common.zip"
  layer_name          = "${var.project_name}-common-${var.environment}"
  compatible_runtimes = ["python3.11"]
  description         = "Common dependencies for AquaSkill functions"

  # Skip if file doesn't exist yet
  lifecycle {
    create_before_destroy = true
  }
}

# Planner Lambda
resource "aws_lambda_function" "planner" {
  filename      = "lambda_functions/planner.zip"
  function_name = "${var.project_name}-planner-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      ENVIRONMENT         = var.environment
      PLANS_BUCKET        = aws_s3_bucket.plans.bucket
      REVIT_DATA_BUCKET   = aws_s3_bucket.revit_data.bucket
      LOG_LEVEL           = var.environment == "prod" ? "INFO" : "DEBUG"
    }
  }

  depends_on = [aws_cloudwatch_log_group.planner]

  # Skip if file doesn't exist yet
  lifecycle {
    create_before_destroy = true
  }
}

# Executor Lambda
resource "aws_lambda_function" "executor" {
  filename      = "lambda_functions/executor.zip"
  function_name = "${var.project_name}-executor-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300  # 5 minutes for complex calculations
  memory_size   = 1024

  environment {
    variables = {
      ENVIRONMENT       = var.environment
      PLANS_BUCKET      = aws_s3_bucket.plans.bucket
      RESULTS_BUCKET    = aws_s3_bucket.results.bucket
      REVIT_DATA_BUCKET = aws_s3_bucket.revit_data.bucket
      FOUNDATION_MODEL  = var.foundation_model
      LOG_LEVEL         = var.environment == "prod" ? "INFO" : "DEBUG"
    }
  }

  depends_on = [aws_cloudwatch_log_group.executor]

  lifecycle {
    create_before_destroy = true
  }
}

# Verifier Lambda
resource "aws_lambda_function" "verifier" {
  filename      = "lambda_functions/verifier.zip"
  function_name = "${var.project_name}-verifier-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 512

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      RESULTS_BUCKET   = aws_s3_bucket.results.bucket
      FOUNDATION_MODEL = var.foundation_model
      LOG_LEVEL        = var.environment == "prod" ? "INFO" : "DEBUG"
    }
  }

  depends_on = [aws_cloudwatch_log_group.verifier]

  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# STEP FUNCTIONS - PIPELINE ORCHESTRATION
# =============================================================================

resource "aws_sfn_state_machine" "aquaskill_pipeline" {
  name     = "${var.project_name}-pipeline-${var.environment}"
  role_arn = aws_iam_role.step_functions_exec.arn

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  definition = jsonencode({
    Comment = "AquaSkill Core v2.0 - Plan-then-Execute Pipeline"
    StartAt = "Planner"
    States = {
      Planner = {
        Type     = "Task"
        Resource = aws_lambda_function.planner.arn
        Parameters = {
          "project_id.$"        = "$.project_id"
          "hazard_class.$"      = "$.hazard_class"
          "remote_area.$"       = "$.remote_area"
          "available_pressure.$" = "$.available_pressure"
        }
        ResultPath = "$.plan_result"
        Next       = "CheckPlanStatus"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PlannerFailed"
            ResultPath  = "$.error"
          }
        ]
      }

      CheckPlanStatus = {
        Type    = "Choice"
        Choices = [
          {
            Variable      = "$.plan_result.status"
            StringEquals  = "READY_TO_EXECUTE"
            Next          = "ExecuteSteps"
          }
        ]
        Default = "PlannerFailed"
      }

      ExecuteSteps = {
        Type     = "Task"
        Resource = aws_lambda_function.executor.arn
        Parameters = {
          "project_id.$" = "$.project_id"
          "plan.$"       = "$.plan_result"
        }
        ResultPath = "$.execution_result"
        Next       = "Verifier"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.TooManyRequestsException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "ExecutorFailed"
            ResultPath  = "$.error"
          }
        ]
      }

      Verifier = {
        Type     = "Task"
        Resource = aws_lambda_function.verifier.arn
        Parameters = {
          "project_id.$"       = "$.project_id"
          "execution_result.$" = "$.execution_result"
        }
        ResultPath = "$.verification_result"
        Next       = "CheckVerificationStatus"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "VerifierFailed"
            ResultPath  = "$.error"
          }
        ]
      }

      CheckVerificationStatus = {
        Type    = "Choice"
        Choices = [
          {
            Variable      = "$.verification_result.traffic_light"
            StringEquals  = "GREEN"
            Next          = "PipelineSuccess"
          },
          {
            Variable      = "$.verification_result.traffic_light"
            StringEquals  = "YELLOW"
            Next          = "PipelineWarning"
          }
        ]
        Default = "PipelineFailed"
      }

      PipelineSuccess = {
        Type   = "Pass"
        Result = { status = "SUCCESS", message = "Ready for Fabrication" }
        ResultPath = "$.final_status"
        End    = true
      }

      PipelineWarning = {
        Type   = "Pass"
        Result = { status = "WARNING", message = "Requires Engineer Review" }
        ResultPath = "$.final_status"
        End    = true
      }

      PipelineFailed = {
        Type   = "Fail"
        Error  = "VerificationFailed"
        Cause  = "Design does not meet NFPA 13 requirements"
      }

      PlannerFailed = {
        Type   = "Fail"
        Error  = "PlannerError"
        Cause  = "Failed to generate execution plan"
      }

      ExecutorFailed = {
        Type   = "Fail"
        Error  = "ExecutorError"
        Cause  = "Failed during execution steps"
      }

      VerifierFailed = {
        Type   = "Fail"
        Error  = "VerifierError"
        Cause  = "Failed during verification"
      }
    }
  })
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "s3_buckets" {
  description = "S3 bucket names"
  value = {
    plans      = aws_s3_bucket.plans.bucket
    results    = aws_s3_bucket.results.bucket
    revit_data = aws_s3_bucket.revit_data.bucket
    nfpa_docs  = aws_s3_bucket.nfpa_docs.bucket
  }
}

output "lambda_functions" {
  description = "Lambda function ARNs"
  value = {
    planner  = aws_lambda_function.planner.arn
    executor = aws_lambda_function.executor.arn
    verifier = aws_lambda_function.verifier.arn
  }
}

output "step_functions_arn" {
  description = "Step Functions state machine ARN"
  value       = aws_sfn_state_machine.aquaskill_pipeline.arn
}

output "cloudwatch_log_groups" {
  description = "CloudWatch Log Group names"
  value = {
    planner        = aws_cloudwatch_log_group.planner.name
    executor       = aws_cloudwatch_log_group.executor.name
    verifier       = aws_cloudwatch_log_group.verifier.name
    step_functions = aws_cloudwatch_log_group.step_functions.name
  }
}

# =============================================================================
# NOTES FOR PRODUCTION DEPLOYMENT
# =============================================================================
#
# Before deploying:
# 1. Create Lambda deployment packages:
#    - lambda_functions/planner.zip
#    - lambda_functions/executor.zip
#    - lambda_functions/verifier.zip
#    - lambda_layers/aquaskill_common.zip
#
# 2. Upload NFPA 13 documents to nfpa_docs bucket for Knowledge Base
#
# 3. Configure Bedrock Knowledge Base manually (not yet in Terraform provider)
#
# 4. Enable S3 backend for state management in production
#
# 5. Set up API Gateway for external triggering (optional)
#
# =============================================================================

# =============================================================================
# AquaSkill - Bedrock Agent with Action Groups
# =============================================================================
# Full Bedrock Agent configuration for LOD 500 autonomous pipeline
#
# Action Groups:
# 1. FileSanitization - Hebrew/DXF fixes
# 2. HydraulicEngine - Hazen-Williams calculations
# 3. NFPAValidator - NFPA 13 compliance checks
# 4. PlannerExecutor - Plan-then-Execute orchestration
#
# Author: AquaBrain V10.0 Platinum
# Date: 2025-12-06
# =============================================================================

# =============================================================================
# BEDROCK AGENT
# =============================================================================

resource "aws_bedrockagent_agent" "aquaskill" {
  agent_name                  = "${var.project_name}-architect-${var.environment}"
  agent_resource_role_arn     = aws_iam_role.bedrock_agent.arn
  foundation_model            = var.foundation_model
  idle_session_ttl_in_seconds = 1800  # 30 minutes

  instruction = <<-EOT
    You are AquaSkill, an expert AI architect for fire sprinkler system design.

    Your capabilities:
    1. File Processing: Fix Hebrew encoding in DXF/DWG files
    2. Hydraulic Calculations: Hazen-Williams pressure loss analysis
    3. NFPA 13 Validation: Check designs against code requirements
    4. LOD 500 Generation: Create fabrication-ready models

    Guidelines:
    - Always cite NFPA 13 section numbers for any requirement you mention
    - Calculate hydraulic losses using Hazen-Williams formula
    - Use Israeli Standard ת"י 1596 for water tank sizing
    - Generate Traffic Light status (GREEN/YELLOW/RED) for all validations
    - Create audit trail with timestamps for all operations

    When asked to process a file:
    1. First call FileSanitization to fix encoding
    2. Then extract geometry data
    3. Run hydraulic calculations
    4. Validate against NFPA 13
    5. Generate final report with BOM

    Always respond in Hebrew when the user writes in Hebrew.
  EOT

  tags = {
    Name = "AquaSkill Architect Agent"
  }
}

# Agent Alias (for versioning)
resource "aws_bedrockagent_agent_alias" "production" {
  agent_alias_name = "production"
  agent_id         = aws_bedrockagent_agent.aquaskill.id
  description      = "Production alias for AquaSkill agent"
}

# =============================================================================
# IAM ROLE FOR BEDROCK AGENT
# =============================================================================

resource "aws_iam_role" "bedrock_agent" {
  name = "${var.project_name}-bedrock-agent-${var.environment}"

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
          ArnLike = {
            "aws:SourceArn" = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "bedrock_agent_invoke" {
  name = "${var.project_name}-bedrock-invoke-policy"
  role = aws_iam_role.bedrock_agent.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.foundation_model}"
      },
      {
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = [
          aws_lambda_function.hebrew_fixer.arn,
          aws_lambda_function.hydraulic_engine.arn,
          aws_lambda_function.nfpa_validator.arn,
          aws_lambda_function.planner_executor.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.plans.arn}/*",
          "${aws_s3_bucket.results.arn}/*",
          "${aws_s3_bucket.revit_data.arn}/*"
        ]
      }
    ]
  })
}

# =============================================================================
# ACTION GROUP LAMBDAS
# =============================================================================

# Hebrew/DXF Fixer Lambda
resource "aws_lambda_function" "hebrew_fixer" {
  filename      = "lambda_functions/hebrew_fixer.zip"
  function_name = "${var.project_name}-hebrew-fixer-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300  # 5 minutes for large files
  memory_size   = 1024

  environment {
    variables = {
      ENVIRONMENT = var.environment
      INPUT_BUCKET = aws_s3_bucket.revit_data.bucket
      OUTPUT_BUCKET = aws_s3_bucket.results.bucket
    }
  }

  # ezdxf layer for DXF processing
  layers = [
    "arn:aws:lambda:${var.aws_region}:770693421928:layer:Klayers-p311-ezdxf:1"
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# Hydraulic Engine Lambda
resource "aws_lambda_function" "hydraulic_engine" {
  filename      = "lambda_functions/hydraulic_engine.zip"
  function_name = "${var.project_name}-hydraulic-engine-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 512

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# NFPA Validator Lambda
resource "aws_lambda_function" "nfpa_validator" {
  filename      = "lambda_functions/nfpa_validator.zip"
  function_name = "${var.project_name}-nfpa-validator-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Planner-Executor Lambda
resource "aws_lambda_function" "planner_executor" {
  filename      = "lambda_functions/planner_executor.zip"
  function_name = "${var.project_name}-planner-executor-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 1024

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      PLANS_BUCKET     = aws_s3_bucket.plans.bucket
      RESULTS_BUCKET   = aws_s3_bucket.results.bucket
      FOUNDATION_MODEL = var.foundation_model
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Lambda permissions for Bedrock Agent
resource "aws_lambda_permission" "bedrock_hebrew_fixer" {
  statement_id  = "AllowBedrockInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.hebrew_fixer.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.aquaskill.agent_arn
}

resource "aws_lambda_permission" "bedrock_hydraulic" {
  statement_id  = "AllowBedrockInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.hydraulic_engine.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.aquaskill.agent_arn
}

resource "aws_lambda_permission" "bedrock_nfpa" {
  statement_id  = "AllowBedrockInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.nfpa_validator.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.aquaskill.agent_arn
}

resource "aws_lambda_permission" "bedrock_planner" {
  statement_id  = "AllowBedrockInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.planner_executor.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.aquaskill.agent_arn
}

# =============================================================================
# ACTION GROUPS
# =============================================================================

# Action Group 1: File Sanitization
resource "aws_bedrockagent_agent_action_group" "file_sanitization" {
  agent_id          = aws_bedrockagent_agent.aquaskill.id
  agent_version     = "DRAFT"
  action_group_name = "FileSanitization"
  description       = "Fix Hebrew encoding and process DXF/DWG files"

  action_group_executor {
    lambda = aws_lambda_function.hebrew_fixer.arn
  }

  api_schema {
    payload = file("${path.module}/schemas/file_sanitization_api.json")
  }
}

# Action Group 2: Hydraulic Engine
resource "aws_bedrockagent_agent_action_group" "hydraulic_engine" {
  agent_id          = aws_bedrockagent_agent.aquaskill.id
  agent_version     = "DRAFT"
  action_group_name = "HydraulicEngine"
  description       = "Calculate pressure loss using Hazen-Williams formula"

  action_group_executor {
    lambda = aws_lambda_function.hydraulic_engine.arn
  }

  api_schema {
    payload = file("${path.module}/schemas/hydraulic_engine_api.json")
  }
}

# Action Group 3: NFPA Validator
resource "aws_bedrockagent_agent_action_group" "nfpa_validator" {
  agent_id          = aws_bedrockagent_agent.aquaskill.id
  agent_version     = "DRAFT"
  action_group_name = "NFPAValidator"
  description       = "Validate designs against NFPA 13 requirements"

  action_group_executor {
    lambda = aws_lambda_function.nfpa_validator.arn
  }

  api_schema {
    payload = file("${path.module}/schemas/nfpa_validator_api.json")
  }
}

# Action Group 4: Planner-Executor
resource "aws_bedrockagent_agent_action_group" "planner_executor" {
  agent_id          = aws_bedrockagent_agent.aquaskill.id
  agent_version     = "DRAFT"
  action_group_name = "PlannerExecutor"
  description       = "Build and execute LOD 500 design plans"

  action_group_executor {
    lambda = aws_lambda_function.planner_executor.arn
  }

  api_schema {
    payload = file("${path.module}/schemas/planner_executor_api.json")
  }
}

# =============================================================================
# DYNAMODB FOR SESSION STATE
# =============================================================================

resource "aws_dynamodb_table" "agent_memory" {
  name         = "${var.project_name}-session-state-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "SessionId"
  range_key    = "Timestamp"

  attribute {
    name = "SessionId"
    type = "S"
  }

  attribute {
    name = "Timestamp"
    type = "N"
  }

  attribute {
    name = "ProjectId"
    type = "S"
  }

  global_secondary_index {
    name            = "ProjectIndex"
    hash_key        = "ProjectId"
    range_key       = "Timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ExpirationTime"
    enabled        = true
  }

  tags = {
    Name = "AquaSkill Session State"
  }
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "bedrock_agent_id" {
  description = "Bedrock Agent ID"
  value       = aws_bedrockagent_agent.aquaskill.id
}

output "bedrock_agent_arn" {
  description = "Bedrock Agent ARN"
  value       = aws_bedrockagent_agent.aquaskill.agent_arn
}

output "bedrock_agent_alias_id" {
  description = "Production alias ID"
  value       = aws_bedrockagent_agent_alias.production.agent_alias_id
}

output "action_group_lambdas" {
  description = "Action Group Lambda ARNs"
  value = {
    hebrew_fixer     = aws_lambda_function.hebrew_fixer.arn
    hydraulic_engine = aws_lambda_function.hydraulic_engine.arn
    nfpa_validator   = aws_lambda_function.nfpa_validator.arn
    planner_executor = aws_lambda_function.planner_executor.arn
  }
}

output "dynamodb_table" {
  description = "Session state table name"
  value       = aws_dynamodb_table.agent_memory.name
}

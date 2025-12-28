# =============================================================================
# AquaSkill Terraform Variables
# =============================================================================

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "aquaskill"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "foundation_model" {
  description = "Bedrock foundation model ID"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

# =============================================================================
# Data Sources
# =============================================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

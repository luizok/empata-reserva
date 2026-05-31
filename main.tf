variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "sa-east-1"
}

variable "environment" {
  description = "Environment name (e.g. dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name used as prefix for resource names"
  type        = string
  default     = "empata-reserva"
}

variable "docker_image_uri" {
  description = "Full URI of the Docker image in ECR (e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/my-image:latest)"
  type        = string
}

variable "lambda_memory_mb" {
  description = "Lambda memory in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 300
}

variable "base_url" {
  description = "Url base da api"
  type        = string
}

variable "iana_tz" {
  description = "Timezone in IANA standard"
  type        = string
}

terraform {
  backend "s3" {}
}

terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  default_tags {
    tags = {
      project = var.project_name
    }
  }
}

# RESOURCES

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "lambda_read_ssm" {
  statement {
    sid    = "GetSSMParameters"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
    ]
    resources = [aws_ssm_parameter.gacc_creds.arn]
  }
}

resource "aws_iam_role_policy" "lambda_read_ssm" {
  name   = "read-ssm-parameters"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_read_ssm.json
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.project_name}-${var.environment}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "scheduler_invoke_lambda" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.this.arn]
  }
}

resource "aws_iam_role" "scheduler_exec" {
  name               = "${var.project_name}-${var.environment}-scheduler-exec"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

resource "aws_iam_role_policy" "scheduler_invoke_lambda" {
  name   = "invoke-lambda"
  role   = aws_iam_role.scheduler_exec.id
  policy = data.aws_iam_policy_document.scheduler_invoke_lambda.json
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}"
  retention_in_days = 30
}

resource "aws_ssm_parameter" "gacc_creds" {
  name  = "/${var.project_name}/${var.environment}/GACCOUNT_CREDENTIALS"
  value = "foo"
  type  = "String"
}

resource "aws_lambda_function" "this" {
  function_name = "${var.project_name}-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  description   = "Empata reserva"

  package_type = "Image"
  image_uri    = var.docker_image_uri

  memory_size = var.lambda_memory_mb
  timeout     = var.lambda_timeout_seconds

  environment {
    variables = {
      BASE_URL                 = var.base_url
      IANA_TZ                  = var.iana_tz
      SSM_GACCOUNT_CREDENTIALS = aws_ssm_parameter.gacc_creds.name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_logs,
    aws_cloudwatch_log_group.lambda,
  ]
}

resource "aws_scheduler_schedule" "every_15_min" {
  name        = "${var.project_name}-${var.environment}-every-15min"
  group_name  = "default"
  description = "Triggers ${aws_lambda_function.this.function_name} every 15 minutes"

  schedule_expression          = "rate(15 minutes)"
  schedule_expression_timezone = var.iana_tz

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.this.arn
    role_arn = aws_iam_role.scheduler_exec.arn

    retry_policy {
      maximum_retry_attempts       = 2
      maximum_event_age_in_seconds = 300
    }
  }
}

# OUTPUTS

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.this.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.this.arn
}

output "scheduler_arn" {
  description = "ARN of the EventBridge Scheduler"
  value       = aws_scheduler_schedule.every_15_min.arn
}

output "lambda_log_group" {
  description = "CloudWatch Log Group for the Lambda function"
  value       = aws_cloudwatch_log_group.lambda.name
}
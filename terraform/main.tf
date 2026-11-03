locals {
  prefix   = "${var.project}-${var.environment}"
  tags     = { Project = var.project, Environment = var.environment, ManagedBy = "Terraform" }
  handlers = toset(["submit", "status", "result", "validate", "authorize", "provider", "success", "failure"])
}

data "archive_file" "lambdas" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/edr-lambdas.zip"
}

resource "aws_dynamodb_table" "requests" {
  name         = "${local.prefix}-requests"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "requestId"
  attribute {
    name = "requestId"
    type = "S"
  }
  point_in_time_recovery { enabled = true }
  server_side_encryption { enabled = true }
  tags = local.tags
}

resource "aws_secretsmanager_secret" "provider" {
  name                    = "${local.prefix}-provider-credentials"
  description             = "Optional provider token; set secret VALUE separately and never via Terraform state"
  recovery_window_in_days = 7
  tags                    = local.tags
}

resource "aws_cloudwatch_log_group" "lambdas" {
  for_each          = local.handlers
  name              = "/aws/lambda/${local.prefix}-${each.key}"
  retention_in_days = 14
  tags              = local.tags
}

resource "aws_lambda_function" "handlers" {
  for_each         = local.handlers
  function_name    = "${local.prefix}-${each.key}"
  filename         = data.archive_file.lambdas.output_path
  source_code_hash = data.archive_file.lambdas.output_base64sha256
  runtime          = "python3.12"
  handler          = "handlers.${each.key}.handler"
  role             = aws_iam_role.lambda[each.key].arn
  timeout          = each.key == "provider" ? 15 : 10
  memory_size      = 128
  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.requests.name
      STATE_MACHINE_ARN = each.key == "submit" ? format(
        "arn:%s:states:%s:%s:stateMachine:%s",
        split(":", aws_iam_role.stepfunctions.arn)[1],
        var.region,
        split(":", aws_iam_role.stepfunctions.arn)[4],
        "${local.prefix}-workflow"
      ) : "unused"
      PROVIDER_SECRET_ARN = aws_secretsmanager_secret.provider.arn
      EDR_ALLOWED_OPERATIONS = contains(
        ["submit", "authorize"],
        each.key
      ) ? jsonencode(var.allowed_operations) : "{}"
    }
  }
  depends_on = [aws_cloudwatch_log_group.lambdas]
  tags       = local.tags
}

resource "aws_cloudwatch_log_group" "stepfunctions" {
  name              = "/aws/states/${local.prefix}"
  retention_in_days = 14
  tags              = local.tags
}

resource "aws_sfn_state_machine" "edr" {
  name     = "${local.prefix}-workflow"
  role_arn = aws_iam_role.stepfunctions.arn
  type     = "STANDARD"
  definition = templatefile("${path.module}/../stepfunctions/workflow.asl.json", {
    table_name    = aws_dynamodb_table.requests.name
    validate_arn  = aws_lambda_function.handlers["validate"].arn
    authorize_arn = aws_lambda_function.handlers["authorize"].arn
    provider_arn  = aws_lambda_function.handlers["provider"].arn
    success_arn   = aws_lambda_function.handlers["success"].arn
    failure_arn   = aws_lambda_function.handlers["failure"].arn
  })
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.stepfunctions.arn}:*"
    include_execution_data = false
    level                  = "ERROR"
  }
  tags = local.tags
}

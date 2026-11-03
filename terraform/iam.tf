data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}
data "aws_iam_policy_document" "sfn_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}
resource "aws_iam_role" "lambda" {
  for_each           = local.handlers
  name               = "${local.prefix}-${each.key}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
  tags               = local.tags
}
resource "aws_iam_role_policy" "lambda" {
  for_each = local.handlers
  name     = "${local.prefix}-${each.key}-policy"
  role     = aws_iam_role.lambda[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [{ Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.lambdas[each.key].arn}:*" }],
      contains(["submit", "status", "result", "success", "failure"], each.key) ? [{
        Effect   = "Allow"
        Action   = each.key == "submit" ? ["dynamodb:PutItem", "dynamodb:UpdateItem"] : contains(["status", "result"], each.key) ? ["dynamodb:GetItem"] : ["dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.requests.arn
      }] : [],
      each.key == "submit" ? [{ Effect = "Allow", Action = ["states:StartExecution"], Resource = aws_sfn_state_machine.edr.arn }] : []
    )
  })
}
resource "aws_iam_role" "stepfunctions" {
  name               = "${local.prefix}-sfn-role"
  assume_role_policy = data.aws_iam_policy_document.sfn_trust.json
  tags               = local.tags
}
resource "aws_iam_role_policy" "stepfunctions" {
  name = "${local.prefix}-sfn-policy"
  role = aws_iam_role.stepfunctions.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "InvokeWorkflowLambdas"
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]

        Resource = [
          for name in [
            "validate",
            "authorize",
            "provider",
            "success",
            "failure"
          ] : aws_lambda_function.handlers[name].arn
        ]
      },
      {
        Sid    = "CloudWatchLogsDelivery"
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

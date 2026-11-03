output "api_url" { value = "https://${aws_api_gateway_rest_api.edr.id}.execute-api.${var.region}.amazonaws.com/${aws_api_gateway_stage.edr.stage_name}" }
output "workflow_arn" { value = aws_sfn_state_machine.edr.arn }
output "secret_arn" { value = aws_secretsmanager_secret.provider.arn }

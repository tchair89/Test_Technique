resource "aws_api_gateway_rest_api" "edr" {
  name = "${local.prefix}-api"
  endpoint_configuration { types = ["REGIONAL"] }
  tags = local.tags
}
resource "aws_api_gateway_resource" "requests" {
  rest_api_id = aws_api_gateway_rest_api.edr.id
  parent_id   = aws_api_gateway_rest_api.edr.root_resource_id
  path_part   = "requests"
}
resource "aws_api_gateway_resource" "request_id" {
  rest_api_id = aws_api_gateway_rest_api.edr.id
  parent_id   = aws_api_gateway_resource.requests.id
  path_part   = "{requestId}"
}
resource "aws_api_gateway_resource" "result" {
  rest_api_id = aws_api_gateway_rest_api.edr.id
  parent_id   = aws_api_gateway_resource.request_id.id
  path_part   = "result"
}
locals {
  routes = {
    submit = { method = "POST", resource_id = aws_api_gateway_resource.requests.id }
    status = { method = "GET", resource_id = aws_api_gateway_resource.request_id.id }
    result = { method = "GET", resource_id = aws_api_gateway_resource.result.id }
  }
}
resource "aws_api_gateway_method" "routes" {
  for_each      = local.routes
  rest_api_id   = aws_api_gateway_rest_api.edr.id
  resource_id   = each.value.resource_id
  http_method   = each.value.method
  authorization = "AWS_IAM"
}
resource "aws_api_gateway_integration" "routes" {
  for_each                = local.routes
  rest_api_id             = aws_api_gateway_rest_api.edr.id
  resource_id             = each.value.resource_id
  http_method             = aws_api_gateway_method.routes[each.key].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.handlers[each.key].invoke_arn
}
resource "aws_lambda_permission" "api" {
  for_each      = local.routes
  statement_id  = "AllowApiGateway-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.handlers[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.edr.execution_arn}/*/${each.value.method}${each.key == "submit" ? "/requests" : each.key == "status" ? "/requests/*" : "/requests/*/result"}"
}
resource "aws_api_gateway_deployment" "edr" {
  rest_api_id = aws_api_gateway_rest_api.edr.id
  triggers    = { redeployment = sha1(jsonencode({ methods = [for r in aws_api_gateway_method.routes : r.id], integrations = [for r in aws_api_gateway_integration.routes : r.id] })) }
  lifecycle { create_before_destroy = true }
}
resource "aws_api_gateway_stage" "edr" {
  rest_api_id   = aws_api_gateway_rest_api.edr.id
  deployment_id = aws_api_gateway_deployment.edr.id
  stage_name    = var.environment
  tags          = local.tags
}
resource "aws_api_gateway_method_settings" "throttle" {
  rest_api_id = aws_api_gateway_rest_api.edr.id
  stage_name  = aws_api_gateway_stage.edr.stage_name
  method_path = "*/*"
  settings {
    throttling_rate_limit  = var.api_rate_limit
    throttling_burst_limit = var.api_burst_limit
    metrics_enabled        = true
  }
}

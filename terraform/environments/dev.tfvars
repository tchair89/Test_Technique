project         = "edr"
environment     = "dev"
region          = "eu-west-3"
offline_plan    = true
api_rate_limit  = 5
api_burst_limit = 10
allowed_operations = {
  "arn:aws:iam::123456789012:user/example" = [
    "get-vehicle-status",
    "get-recalls"
  ]
}
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 6.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.0" }
  }
}
provider "aws" {
  region                      = var.region
  access_key                  = var.offline_plan ? "offline" : null
  secret_key                  = var.offline_plan ? "offline" : null
  skip_credentials_validation = var.offline_plan
  skip_metadata_api_check     = var.offline_plan
  skip_requesting_account_id  = var.offline_plan
}

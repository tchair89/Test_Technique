variable "project" {
  type    = string
  default = "edr"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "region" {
  type    = string
  default = "eu-west-3"
}

variable "offline_plan" {
  type    = bool
  default = true
}

variable "api_rate_limit" {
  type    = number
  default = 5
}

variable "api_burst_limit" {
  type    = number
  default = 10
}

variable "allowed_operations" {
  description = "Demo authorization policy indexed by IAM caller ARN"
  type        = map(list(string))
  default     = {}
}

variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
  default = "government-assistant-001"
}

variable "region" {
  description = "Google Cloud region"
  type        = string
  default     = "us-central1"
}

variable "credentials_file" {
  description = "Path to the GCP credentials JSON file"
  type        = string
  default     = "/home/karol/terraform-gov-assistant-key.json"
}

variable "repo_name" {
  description = "Name of the Docker repository"
  type        = string
  default     = "government-assistant-docker-repo"
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "government-assistant-api"
}

variable "image_name" {
  description = "Name of the Docker image"
  type        = string
  default     = "government-assistant-api"
}

variable "xai_api_key" {
  description = "API Key for external service"
  type        = string
}


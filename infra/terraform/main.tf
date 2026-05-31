# Optional: deploy env for home host with public IPv6 API

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

variable "project_name" {
  type    = string
  default = "eta-ml"
}

variable "compose_host" {
  type        = string
  description = "Local hostname or LAN IP for Postgres/MLflow (internal)"
  default     = "localhost"
}

variable "eta_api_public_url" {
  type        = string
  description = "Public ETA API URL (IPv6)"
  default     = "http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000"
}

resource "local_file" "deploy_env" {
  filename = "${path.module}/generated.env"
  content  = <<-EOT
    PROJECT_NAME=${var.project_name}
    COMPOSE_HOST=${var.compose_host}
    DATABASE_URL=postgresql://eta:eta@${var.compose_host}:5432/eta_db
    MLFLOW_TRACKING_URI=http://${var.compose_host}:5000
    ETA_PUBLIC_BASE_URL=${var.eta_api_public_url}
    ETA_API_URL=${var.eta_api_public_url}
  EOT
}

output "eta_api_public_url" {
  value       = var.eta_api_public_url
  description = "Public IPv6 ETA API"
}

output "eta_api_health_url" {
  value = "${var.eta_api_public_url}/health"
}

output "mlflow_url" {
  value = "http://${var.compose_host}:5000"
}

output "airflow_url" {
  value = "http://${var.compose_host}:8080"
}

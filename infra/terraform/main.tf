# Optional: generate local deploy env (localhost URLs)

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
  description = "Host for Docker services on the machine"
  default     = "localhost"
}

variable "eta_api_url" {
  type        = string
  description = "ETA API URL (local only)"
  default     = "http://localhost:8000"
}

variable "grafana_url" {
  type        = string
  description = "Grafana URL on host (external access via tunnel4)"
  default     = "http://localhost:3000"
}

resource "local_file" "deploy_env" {
  filename = "${path.module}/generated.env"
  content  = <<-EOT
    PROJECT_NAME=${var.project_name}
    COMPOSE_HOST=${var.compose_host}
    DATABASE_URL=postgresql://eta:eta@${var.compose_host}:5432/eta_db
    MLFLOW_TRACKING_URI=http://${var.compose_host}:5000
    ETA_PUBLIC_BASE_URL=${var.eta_api_url}
    ETA_API_URL=${var.eta_api_url}
    MLFLOW_PUBLIC_URL=http://${var.compose_host}:5000
    PROMETHEUS_PUBLIC_URL=http://${var.compose_host}:9090
    GRAFANA_PUBLIC_URL=${var.grafana_url}
    AIRFLOW_PUBLIC_URL=http://${var.compose_host}:8080
  EOT
}

output "eta_api_url" {
  value       = var.eta_api_url
  description = "ETA API (localhost)"
}

output "eta_api_health_url" {
  value = "${var.eta_api_url}/health"
}

output "grafana_url" {
  value       = var.grafana_url
  description = "Grafana on host; expose via tunnel4"
}

output "mlflow_url" {
  value = "http://${var.compose_host}:5000"
}

output "prometheus_url" {
  value = "http://${var.compose_host}:9090"
}

output "airflow_url" {
  value = "http://${var.compose_host}:8080"
}

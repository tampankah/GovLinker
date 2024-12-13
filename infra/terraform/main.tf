resource "google_artifact_registry_repository" "docker_repo" {
  repository_id = var.repo_name
  format       = "DOCKER"
  location     = var.region
  description  = "Docker repository for storing container images"
}

resource "google_cloud_run_service" "api_service" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.name}/${var.image_name}"
        env {
          name  = "XAI_API_KEY"
          value = var.xai_api_key
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}
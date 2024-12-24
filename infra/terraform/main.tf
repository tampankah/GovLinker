
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
        image = "gcr.io/google-containers/pause:3.1" # Tymczasowy obraz (minimalny).
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}
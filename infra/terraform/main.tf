
resource "google_artifact_registry_repository" "docker_repo" {
  repository_id = var.repo_name
  format       = "DOCKER"
  location     = var.region
  description  = "Docker repository for storing container images"
}

resource "google_storage_bucket" "frontend_bucket" {
  name     = var.frontend_bucket_name
  location = var.region
}
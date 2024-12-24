
resource "google_artifact_registry_repository" "docker_repo" {
  repository_id = var.repo_name
  format       = "DOCKER"
  location     = var.region
  description  = "Docker repository for storing container images"
}

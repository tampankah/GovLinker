output "docker_repo_url" {
  description = "The URL of the Docker repository"
  value       = "us-central1-docker.pkg.dev/${var.project_id}/${var.repo_name}"
}

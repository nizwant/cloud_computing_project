output "db_instance_connection_name" {
  value = google_sql_database_instance.default.connection_name
}

output "db_user" {
  value = google_sql_user.appuser.name
}

output "db_name" {
  value = google_sql_database.db.name
}

output "db_password" {
  value     = random_password.db_password.result
  sensitive = true
}

output "repository_url" {
  description = "The URL to access the Docker repository."
  value       = "${google_artifact_registry_repository.my_simple_repo.location}-docker.pkg.dev/${google_artifact_registry_repository.my_simple_repo.project}/${google_artifact_registry_repository.my_simple_repo.repository_id}"
}

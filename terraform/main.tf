resource "google_app_engine_application" "app" {
  project     = var.project_id
  location_id = var.region_app_engine
}



# ------------ CLOUD-SQL -------------
resource "google_sql_database_instance" "default" {
  name             = "sql-db-instance"
  project          = var.project_id
  region           = var.region
  database_version = var.db_version

  settings {
    tier = var.db_tier
  }

  deletion_protection = false
}

resource "google_sql_database" "db" {
  name     = var.db_name
  instance = google_sql_database_instance.default.name
}

resource "random_password" "db_password" {
  length  = 16
  special = true
}

resource "google_sql_user" "appuser" {
  name        = "appuser"
  instance    = google_sql_database_instance.default.name
  password_wo = random_password.db_password.result
}

data "google_app_engine_default_service_account" "default" {
  project = var.project_id
}

resource "google_project_iam_member" "appengine_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${data.google_app_engine_default_service_account.default.email}"
}

# -------- PUB-SUB -------------------
resource "google_pubsub_topic" "my_topic" {
  name = "songs-to-process"
}

resource "google_pubsub_subscription" "my_subscription" {
  name  = "sub-songs-to-process"
  topic = google_pubsub_topic.my_topic.name
}


# -------- Artefact registry -------------------
resource "google_artifact_registry_repository" "my_simple_repo" {
  location      = var.region
  repository_id = "test-repo-name"
  format        = "DOCKER"
}

output "repository_url" {
  description = "The URL to access the Docker repository."
  value       = "${google_artifact_registry_repository.my_simple_repo.location}-docker.pkg.dev/${google_artifact_registry_repository.my_simple_repo.project}/${google_artifact_registry_repository.my_simple_repo.repository_id}"
}
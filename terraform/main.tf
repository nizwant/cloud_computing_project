# ------------ App-Engine -------------
resource "google_app_engine_application" "app" {
  project     = var.project_id
  location_id = var.region_app_engine
}


# ------------ Cloud-SQL -------------
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


# -------- Pub-Sub -------------------
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


# -------- Cloud Run -------------------
resource "google_cloud_run_v2_service" "my-cloud-run-service" {
  name     = "crawler-cloud-run"
  location = var.region

  template {
    containers {
      image = "us-central1-docker.pkg.dev/your-project-id/your-repository/your-image:latest"
      # Example: us-central1-docker.pkg.dev/my-project/my-repo/my-image:latest
      ports {
        container_port = 8080
      }
      resources{
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }
    }
    scaling {
      max_instance_count = 2
      min_instance_count = 0
    }
  }
}


# -------- Cloud Functions -------------------

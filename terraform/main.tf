# Configure the Google Cloud Provider
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.18.0" # Or the latest version
    }
  }
}

# Replace with your GCP project ID and region
variable "project_id" {
  description = "The ID of the Google Cloud project"
  type        = string
  default     = "your-project-id" # Change this
}

variable "region" {
  description = "The region to deploy resources"
  type        = string
  default     = "us-central1" # Change this
}

variable "zone" {
  description = "The zone to deploy resources"
  type        = string
  default     = "us-central1-a" # Change this
}

# 1. Cloud SQL Instance
resource "google_sql_database_instance" "cloud_sql" {
  name             = "cloud-sql-instance"
  region           = var.region
  project          = var.project_id
  database_version = "POSTGRES_15" # Or another supported version

  settings {
    tier = "db-f1-micro" #  For small workloads.  Change as needed.
    availability_type = "ZONAL" # or "REGIONAL" for higher availability
    disk_size = 10 # in GB
    disk_type = "PD_SSD"
    backup_configuration {
      enabled = true
      start_time = "03:00" #  Define backup window.
    }
    ip_configuration {
      ipv4_enabled = false
      private_network = "projects/${var.project_id}/global/networks/default" # Use the default network
    }
  }
}

# Create a private service access connection.  This is needed for Cloud SQL.
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = "projects/${var.project_id}/global/networks/default"
  service                 = "servicenetworking.googleapis.com"
  project                 = var.project_id

  #  Allocate an unused CIDR block.  Important:  Choose a range that does NOT overlap with any existing subnet in your VPC.
  peering_routes = {
    name    = "sql-cidr-allocation"
    primary_ip_range = "10.88.0.0/24" # Example range.  Change as needed.
  }
}

# Cloud SQL Database
resource "google_sql_database" "cloud_sql_database" {
  name       = "mydatabase" # Change this
  instance = google_sql_database_instance.cloud_sql.name
  project  = var.project_id
}

# Cloud SQL User
resource "google_sql_user" "cloud_sql_user" {
  name       = "myuser" # Change this
  instance = google_sql_database_instance.cloud_sql.name
  project  = var.project_id
  password = "mypassword" #  **IMPORTANT:** Use a secret manager in production.  This is insecure!
}

# 2. App Engine Application
resource "google_app_engine_application" "app_engine" {
  project     = var.project_id
  location_id = var.region
}

# 3. Cloud Functions Function
resource "google_cloudfunctions_function" "cloud_function" {
  name                  = "my-cloud-function" # Change this
  runtime               = "python310" # Or another supported runtime
  entry_point           = "hello_world" # Name of the function to execute
  region                = var.region
  project               = var.project_id
  source_archive_bucket = google_storage_bucket.cloud_function_bucket.name
  source_archive_object = google_storage_object.cloud_function_zip.name
  service_account_email = google_service_account.cloud_function_sa.email # Use the service account

  environment_variables = {
    "DB_USER"     = google_sql_user.cloud_sql_user.name
    "DB_PASS"     = "mypassword" # **IMPORTANT:** Use Secret Manager in production
    "DB_NAME"     = google_sql_database.cloud_sql_database.name
    "DB_INSTANCE" = google_sql_database_instance.cloud_sql.connection_name
  }

  #  Define the trigger.  In this case, HTTP.
  https_trigger_security_level = "SECURE_ALWAYS"
}

# Create a service account for the Cloud Function
resource "google_service_account" "cloud_function_sa" {
  account_id   = "cloud-function-sa"
  display_name = "Service Account for Cloud Function"
  project      = var.project_id
}

# Grant the Cloud Function service account permissions to connect to Cloud SQL.
resource "google_project_iam_member" "cloud_function_sql_access" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}

# Grant the Cloud Function service account permissions to write to Pub/Sub
resource "google_project_iam_member" "cloud_function_pubsub_access" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.cloud_function_sa.email}"
}

# Create a bucket to store the Cloud Function's source code.
resource "google_storage_bucket" "cloud_function_bucket" {
  name     = "${var.project_id}-cloud-function-source"
  location = var.region
  project  = var.project_id
  storage_class = "STANDARD"
}

#  Zip the Cloud Function code (you'll need to do this locally or in your CI/CD pipeline).
#  This is a *local* file path.  The Terraform apply will upload it.
data "archive_file" "cloud_function_zip" {
  type        = "zip"
  source_dir  = "./cloud-function" # Path to your Cloud Function code.  Create this directory!
  output_path = "/tmp/cloud-function.zip" #  Temp file.
}

# Upload the zip file to the bucket.
resource "google_storage_object" "cloud_function_zip" {
  name   = "cloud-function-source.zip"
  bucket = google_storage_bucket.cloud_function_bucket.name
  source = data.archive_file.cloud_function_zip.output_path
}


# 4. Load Balancing (for App Engine)
resource "google_compute_address" "app_engine_static_ip" {
  name         = "app-engine-static-ip"
  region       = var.region
  project      = var.project_id
}

resource "google_compute_global_forwarding_rule" "app_engine_forwarding_rule" {
  name       = "app-engine-forwarding-rule"
  target     = google_compute_target_http_proxy.app_engine_http_proxy.id
  ip_address = google_compute_address.app_engine_static_ip.address
  project    = var.project_id
}

resource "google_compute_target_http_proxy" "app_engine_http_proxy" {
  name        = "app-engine-http-proxy"
  url_map     = google_compute_url_map.app_engine_url_map.self_link
  project     = var.project_id
}

resource "google_compute_url_map" "app_engine_url_map" {
  name            = "app-engine-url-map"
  default_service = google_app_engine_service.default.default_hostname #  Important:  Use the *default* service.
  project         = var.project_id
}

# Dummy App Engine service.  Replace with your actual App Engine deployment.
resource "google_app_engine_service" "default" {
  project = var.project_id
  module  = "default" #  "default" is the service name.
  split { #  Even with only one version, a split is needed for load balancing.
    shard_by = "IP" #  or "COOKIE"
    version {
      name = "v1" #  Change this to your version
      resources {
        memory_gb = 0.5
        cpu       = 1
      }
    }
  }
}

# 5. Pub/Sub Topic
resource "google_pubsub_topic" "pubsub_topic" {
  name    = "my-pubsub-topic" # Change this
  project = var.project_id
}

# 6. Cloud Run Service (Subscriber)
resource "google_cloud_run_service" "cloud_run_service" {
  name     = "my-cloud-run-service" # Change this
  location = var.region
  project  = var.project_id

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/my-cloud-run-image:latest" # Change this to your container image
        envs = [
          {
            name  = "DB_USER"
            value = google_sql_user.cloud_sql_user.name
          },
          {
            name  = "DB_PASS"
            value = "mypassword" # **IMPORTANT:** Use Secret Manager
          },
          {
            name  = "DB_NAME"
            value = google_sql_database.cloud_sql_database.name
          },
           {
            name  = "DB_INSTANCE"
            value = google_sql_database_instance.cloud_sql.connection_name
          }
        ]
      }
      service_account_name = google_service_account.cloud_run_sa.email
    }
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"
        "autoscaling.knative.dev/maxScale" = "10" # Or higher, as needed
      }
    }
  }
}

# Create a service account for Cloud Run
resource "google_service_account" "cloud_run_sa" {
  account_id   = "cloud-run-sa"
  display_name = "Service Account for Cloud Run"
  project      = var.project_id
}

# Grant Cloud Run service account the necessary permissions to connect to the Cloud SQL instance.
resource "google_project_iam_member" "cloud_run_sql_access" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Grant the Cloud Run service account permissions to consume messages from the Pub/Sub topic.
resource "google_project_iam_member" "cloud_run_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# 7. Pub/Sub Subscription
resource "google_pubsub_subscription" "pubsub_subscription" {
  name  = "my-pubsub-subscription" # Change this
  topic = google_pubsub_topic.pubsub_topic.name
  project = var.project_id

  #  Use a push subscription to Cloud Run
  push_config {
    push_endpoint = google_cloud_run_service.cloud_run_service.status.0.url
    oidc_service_account_email = google_service_account.cloud_run_sa.email
  }
  ack_deadline = 20 # in seconds
}

# 8. Artifact Registry Repository
resource "google_artifact_registry_repository" "artifact_registry" {
  location      = var.region
  repository_id = "my-docker-repository" # Change this
  project       = var.project_id
  format        = "DOCKER" # Or "MAVEN", "NPM", etc.
}

# Output the important URLs and connection strings
output "app_engine_url" {
  value = google_compute_global_forwarding_rule.app_engine_forwarding_rule.ip_address
  description = "The IP address for accessing the App Engine application"
}

output "cloud_sql_connection_name" {
  value       = google_sql_database_instance.cloud_sql.connection_name
  description = "The Cloud SQL connection name (for connecting from App Engine, Cloud Functions, Cloud Run)"
}

output "cloud_function_url" {
  value = google_cloudfunctions_function.cloud_function.https_trigger_url
  description = "URL of the Cloud Function"
}

output "cloud_run_url" {
  value = google_cloud_run_service.cloud_run_service.status.0.url
  description = "URL of the Cloud Run service"
}

output "artifact_registry_repository_url" {
  value = google_artifact_registry_repository.artifact_registry.id
  description = "Artifact Registry Repository URL"
}

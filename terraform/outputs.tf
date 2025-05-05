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
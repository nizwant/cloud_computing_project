provider "google" {
  credentials = file("~/Downloads/cloud-computing-project-458205-ace66217a40c.json")
  project     = var.project
  region      = var.region
  zone        = var.zone
}

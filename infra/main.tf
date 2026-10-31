locals {
  services       = toset(["cloudfunctions.googleapis.com", "run.googleapis.com", "cloudbuild.googleapis.com", "artifactregistry.googleapis.com", "storage.googleapis.com", "logging.googleapis.com", "monitoring.googleapis.com", "iam.googleapis.com"])
  student_roles  = toset(["roles/monitoring.editor", "roles/logging.viewer", "roles/logging.configWriter", "roles/cloudfunctions.viewer"])
  student_grants = { for pair in setproduct(var.student_members, local.student_roles) : "${pair[0]}|${pair[1]}" => { member = pair[0], role = pair[1] } }
}

resource "google_project_service" "apis" {
  for_each           = local.services
  service            = each.value
  disable_on_destroy = false
}

resource "google_logging_project_bucket_config" "default" {
  project          = var.project_id
  location         = "global"
  bucket_id        = "_Default"
  retention_days   = var.log_retention_days
  enable_analytics = true
  depends_on       = [google_project_service.apis]
}

resource "google_service_account" "runtime" { account_id = "${var.function_name}-run" }
resource "google_service_account" "build" { account_id = "${var.function_name}-build" }

resource "google_project_iam_member" "runtime" {
  for_each = toset(["roles/logging.logWriter", "roles/monitoring.metricWriter"])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.runtime.email}"
}
resource "google_project_iam_member" "build" {
  for_each = toset(["roles/cloudbuild.builds.builder", "roles/logging.logWriter"])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.build.email}"
}
resource "google_project_iam_member" "students" {
  for_each = local.student_grants
  project  = var.project_id
  role     = each.value.role
  member   = each.value.member
}
resource "google_storage_bucket" "source" {
  name                        = "${var.project_id}-${var.function_name}-src"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}
data "archive_file" "source" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/.build/function-source.zip"
}
resource "google_storage_bucket_object" "source" {
  name   = "function-source-${data.archive_file.source.output_md5}.zip"
  bucket = google_storage_bucket.source.name
  source = data.archive_file.source.output_path
}
resource "google_cloudfunctions2_function" "api" {
  name     = var.function_name
  location = var.region
  build_config {
    runtime         = var.runtime
    entry_point     = var.entry_point
    service_account = google_service_account.build.id
    source {
      storage_source {
        bucket = google_storage_bucket.source.name
        object = google_storage_bucket_object.source.name
      }
    }
  }
  service_config {
    available_memory                 = "512Mi"
    available_cpu                    = "1"
    timeout_seconds                  = 60
    min_instance_count               = 0
    max_instance_count               = var.max_instances
    max_instance_request_concurrency = var.concurrency
    service_account_email            = google_service_account.runtime.email
    ingress_settings                 = "ALLOW_ALL"
    environment_variables            = { FAILURE_RATE = tostring(var.failure_rate), EXTRA_LATENCY_MS = tostring(var.extra_latency_ms) }
  }
}
resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.allow_unauthenticated ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloudfunctions2_function.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Logs-based metrics must exist before the workload generator runs because
# they only count entries received after their creation.
resource "google_logging_metric" "request_completed" {
  name        = "orders_request_completed"
  project     = var.project_id
  description = "Completed requests emitted by the orders API."
  filter      = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.function_name}\" AND jsonPayload.message=\"request_completed\""

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "Orders API completed requests"
  }

  depends_on = [google_cloudfunctions2_function.api]
}

resource "google_logging_metric" "client_errors" {
  name        = "orders_client_errors"
  project     = var.project_id
  description = "4xx responses emitted by the orders API."
  filter      = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.function_name}\" AND jsonPayload.status_code>=400 AND jsonPayload.status_code<500"

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "Orders API client errors"
  }

  depends_on = [google_cloudfunctions2_function.api]
}

resource "google_logging_metric" "server_errors" {
  name        = "orders_server_errors"
  project     = var.project_id
  description = "5xx responses emitted by the orders API."
  filter      = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.function_name}\" AND jsonPayload.status_code>=500"

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "Orders API server errors"
  }

  depends_on = [google_cloudfunctions2_function.api]
}

resource "google_logging_metric" "latency_ms" {
  name            = "orders_latency_ms"
  project         = var.project_id
  description     = "Backend latency recorded by the orders API, in milliseconds."
  filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.function_name}\" AND jsonPayload.message=\"request_completed\""
  value_extractor = "EXTRACT(jsonPayload.latency_ms)"

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    unit         = "ms"
    display_name = "Orders API backend latency"
  }

  bucket_options {
    explicit_buckets {
      bounds = [0, 10, 25, 50, 100, 250, 500, 1000, 5000]
    }
  }

  depends_on = [google_cloudfunctions2_function.api]
}

resource "google_monitoring_dashboard" "orders_api" {
  dashboard_json = jsonencode({
    displayName = "Observable Orders API"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          xPos = 0, yPos = 0, width = 6, height = 4
          widget = {
            title = "Cloud Run request rate"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter      = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" resource.label.\"service_name\"=\"${var.function_name}\""
                    aggregation = { alignmentPeriod = "60s", perSeriesAligner = "ALIGN_RATE" }
                  }
                }
              }]
              yAxis = { label = "requests/s", scale = "LINEAR" }
            }
          }
        },
        {
          xPos = 6, yPos = 0, width = 6, height = 4
          widget = {
            title = "Completed requests (logs)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter      = "metric.type=\"logging.googleapis.com/user/orders_request_completed\""
                    aggregation = { alignmentPeriod = "60s", perSeriesAligner = "ALIGN_RATE" }
                  }
                }
              }]
              yAxis = { label = "requests/s", scale = "LINEAR" }
            }
          }
        },
        {
          xPos = 0, yPos = 4, width = 6, height = 4
          widget = {
            title = "4xx and 5xx responses (logs)"
            xyChart = {
              dataSets = [
                { timeSeriesQuery = { timeSeriesFilter = { filter = "metric.type=\"logging.googleapis.com/user/orders_client_errors\"", aggregation = { alignmentPeriod = "60s", perSeriesAligner = "ALIGN_RATE" } } } },
                { timeSeriesQuery = { timeSeriesFilter = { filter = "metric.type=\"logging.googleapis.com/user/orders_server_errors\"", aggregation = { alignmentPeriod = "60s", perSeriesAligner = "ALIGN_RATE" } } } }
              ]
              yAxis = { label = "errors/s", scale = "LINEAR" }
            }
          }
        },
        {
          xPos = 6, yPos = 4, width = 6, height = 4
          widget = {
            title = "Backend latency (logs)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter      = "metric.type=\"logging.googleapis.com/user/orders_latency_ms\""
                    aggregation = { alignmentPeriod = "60s", perSeriesAligner = "ALIGN_DELTA" }
                  }
                }
              }]
              yAxis = { label = "milliseconds", scale = "LINEAR" }
            }
          }
        },
        {
          xPos = 0, yPos = 8, width = 12, height = 4
          widget = {
            title = "Structured request logs"
            logsPanel = {
              filter        = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.function_name}\" AND jsonPayload.message=\"request_completed\""
              resourceNames = ["projects/${var.project_id}"]
            }
          }
        }
      ]
    }
  })

  depends_on = [
    google_logging_metric.request_completed,
    google_logging_metric.client_errors,
    google_logging_metric.server_errors,
    google_logging_metric.latency_ms,
  ]
}

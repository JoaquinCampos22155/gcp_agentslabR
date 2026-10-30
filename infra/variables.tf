variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}
variable "function_name" {
  type    = string
  default = "orders-api"
}
variable "runtime" {
  type    = string
  default = "python313"
}
variable "entry_point" {
  type    = string
  default = "handle"
}
variable "source_dir" {
  type    = string
  default = "../backend"
}
variable "failure_rate" {
  type    = number
  default = 0.02
}
variable "extra_latency_ms" {
  type    = number
  default = 0
}
variable "max_instances" {
  type    = number
  default = 10
}
variable "concurrency" {
  type    = number
  default = 1
}
variable "allow_unauthenticated" {
  type    = bool
  default = true
}
variable "log_retention_days" {
  type    = number
  default = 30
}
variable "student_members" {
  type    = list(string)
  default = []
}

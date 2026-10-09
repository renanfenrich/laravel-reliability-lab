terraform {
  required_version = "= 1.16.5"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.38.0"
    }
  }
}
provider "kubernetes" {
  config_path    = "${path.module}/../.kubeconfig"
  config_context = "kind-laravel-reliability-lab"
}
variable "secrets" {
  type      = map(string)
  sensitive = true
}
resource "kubernetes_namespace_v1" "lab" {
  metadata { name = "lab" }
}
resource "kubernetes_secret_v1" "lab" {
  metadata {
    name      = "lab-secrets"
    namespace = kubernetes_namespace_v1.lab.metadata[0].name
  }
  data = merge(var.secrets, {
    POSTGRES_PASSWORD          = var.secrets["DB_PASSWORD"]
    GF_SECURITY_ADMIN_USER     = "lab"
    GF_SECURITY_ADMIN_PASSWORD = var.secrets["LAB_TOKEN"]
  })
}
resource "kubernetes_manifest" "lab" {
  for_each   = jsondecode(file("${path.module}/manifests.json"))
  manifest   = each.value
  depends_on = [kubernetes_namespace_v1.lab, kubernetes_secret_v1.lab]
}

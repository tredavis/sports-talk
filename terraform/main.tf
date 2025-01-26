terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.11"
    }
  }
}

provider "kubernetes" {
  # Uses local kubeconfig (minikube context)
}

resource "kubernetes_namespace" "sports_talk_ns" {
  metadata {
    name = "sports-talk"
  }
}

resource "kubernetes_deployment" "sports_talk_app" {
  metadata {
    name      = "sports-talk-tf"
    namespace = kubernetes_namespace.sports_talk_ns.metadata[0].name
  }
  spec {
    replicas = 1
    selector {
      match_labels = {
        app = "sports-talk"
      }
    }
    template {
      metadata {
        labels = {
          app = "sports-talk"
        }
      }
      spec {
        container {
          image = "sports-talk:latest"
          name  = "sports-talk"
          port {
            container_port = 80
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "sports_talk_svc" {
  metadata {
    name      = "sports-talk-svc-tf"
    namespace = kubernetes_namespace.sports_talk_ns.metadata[0].name
  }
  spec {
    selector = {
      app = "sports-talk"
    }
    port {
      port        = 80
      target_port = 80
    }
  }
}
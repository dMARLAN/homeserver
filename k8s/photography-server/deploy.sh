#!/bin/bash

# Photography Server K3s Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

echo "Deploying Photography Server to K3s..."

echo "Building Docker images..."
cd "${PROJECT_ROOT_DIR}"
docker build -f photographyserver/api/Dockerfile -t photography-server/api:latest .
docker build -f photographyserver/sync_worker/Dockerfile -t photography-server/sync-worker:latest .
docker build -f photographyserver/frontend/Dockerfile -t photography-server/frontend:latest .

echo "Importing images to k3s..."
docker save photography-server/api:latest | sudo k3s ctr images import -
docker save photography-server/sync-worker:latest | sudo k3s ctr images import -
docker save photography-server/frontend:latest | sudo k3s ctr images import -

echo "Applying Kubernetes manifests..."
cd "${SCRIPT_DIR}"
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f photos-pv.yaml
kubectl apply -f postgres.yaml

echo "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n photography-server --timeout=300s

kubectl apply -f api.yaml
kubectl apply -f sync-worker.yaml
kubectl apply -f frontend.yaml

echo "Deployment complete!"

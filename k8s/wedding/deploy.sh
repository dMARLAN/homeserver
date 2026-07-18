#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [ ! -f secrets.yaml ]; then
    echo "Error: secrets.yaml not found." >&2
    echo "Copy secrets.example.yaml to secrets.yaml, fill in real values, then re-run." >&2
    exit 1
fi

echo "Deploying wedding website stack..."

kubectl apply -f namespace.yaml

kubectl apply -f postgres/pv.yaml
kubectl apply -f api/pv.yaml

kubectl apply -f secrets.yaml
kubectl apply -f api/configmap.yaml

kubectl apply -f postgres/deployment.yaml
kubectl apply -f postgres/service.yaml
echo "Waiting for postgres to become ready..."
kubectl rollout status deployment/postgres -n wedding --timeout=180s

echo "Running database migrations..."
kubectl delete job wedding-migrate -n wedding --ignore-not-found
kubectl apply -f migrate-job.yaml
kubectl wait --for=condition=complete job/wedding-migrate -n wedding --timeout=180s

kubectl apply -f api/deployment.yaml
kubectl apply -f api/service.yaml
kubectl apply -f frontend/deployment.yaml
kubectl apply -f frontend/service.yaml

kubectl apply -f ingress.yaml

echo "Wedding website stack deployed successfully!"
echo ""
echo "🌐 URLs:"
echo "  Site: https://chadandjanina.wedding"
echo "  WWW:  https://www.chadandjanina.wedding"
echo "  API:  https://api.chadandjanina.wedding"
echo ""

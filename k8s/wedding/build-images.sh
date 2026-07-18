#!/bin/bash

set -e

usage() {
    echo "Usage: ${0} <wedding-website-repo-dir>" >&2
    echo "Builds the wedding images from a local wedding-website checkout and imports them into k3s." >&2
    exit 1
}

repo_dir="${1:-}"
if [ -z "${repo_dir}" ]; then
    echo "Error: missing wedding-website repo directory argument." >&2
    usage
fi
if [ ! -e "${repo_dir}/.git" ]; then
    echo "Error: ${repo_dir} is not a git checkout of wedding-website." >&2
    usage
fi

cd "${repo_dir}"

echo "==> Building wedding-api:prod..."
docker build -f src/api/dockerfiles/base.Dockerfile -t wedding-api:prod .

echo "==> Building wedding-frontend:prod..."
docker build -f dockerfiles/frontend.Dockerfile \
    --build-arg NEXT_PUBLIC_API_URL=https://api.chadandjanina.wedding \
    -t wedding-frontend:prod src/frontend

echo "==> Importing wedding-api:prod into k3s containerd..."
docker save wedding-api:prod | k3s ctr -n k8s.io images import -

echo "==> Importing wedding-frontend:prod into k3s containerd..."
docker save wedding-frontend:prod | k3s ctr -n k8s.io images import -

if kubectl get deployment wedding-api wedding-frontend -n wedding > /dev/null 2>&1; then
    echo "==> Restarting wedding deployments..."
    kubectl rollout restart deployment/wedding-api deployment/wedding-frontend -n wedding
else
    echo "==> Wedding deployments not found; skipping restart (first deploy happens via deploy.sh)."
fi

echo "✅ Images built and imported"

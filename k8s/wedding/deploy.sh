#!/bin/bash

set -e

# A dev kind cluster on this machine is the current kubectl context; production must be named.
KUBECTL="${KUBECTL:-kubectl --context homeserver}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [ ! -f secrets.yaml ]; then
    echo "Error: secrets.yaml not found." >&2
    echo "Copy secrets.example.yaml to secrets.yaml, fill in real values, then re-run." >&2
    exit 1
fi

echo "Deploying wedding website stack..."

${KUBECTL} apply -f namespace.yaml

${KUBECTL} apply -f postgres/pv.yaml
${KUBECTL} apply -f api/pv.yaml
${KUBECTL} apply -f mail/pv.yaml
${KUBECTL} apply -f backup/pv.yaml

${KUBECTL} apply -f secrets.yaml
${KUBECTL} apply -f api/configmap.yaml

${KUBECTL} apply -f postgres/deployment.yaml
${KUBECTL} apply -f postgres/service.yaml
echo "Waiting for postgres to become ready..."
${KUBECTL} rollout status deployment/postgres -n wedding --timeout=180s

echo "Running database migrations..."
${KUBECTL} delete job wedding-migrate -n wedding --ignore-not-found
${KUBECTL} apply -f migrate-job.yaml
${KUBECTL} wait --for=condition=complete job/wedding-migrate -n wedding --timeout=180s

${KUBECTL} apply -f mail/configmap.yaml
${KUBECTL} apply -f mail/certificate.yaml
${KUBECTL} apply -f mail/deployment.yaml
${KUBECTL} apply -f mail/service.yaml

${KUBECTL} apply -f api/deployment.yaml
${KUBECTL} apply -f api/service.yaml
${KUBECTL} apply -f frontend/deployment.yaml
${KUBECTL} apply -f frontend/service.yaml

${KUBECTL} apply -f ingress.yaml
${KUBECTL} apply -f backup/cronjob.yaml

echo "Wedding website stack deployed successfully!"
echo ""
echo "🌐 URLs:"
echo "  Site: https://chadandjanina.wedding"
echo "  WWW:  https://www.chadandjanina.wedding"
echo "  API:  https://api.chadandjanina.wedding"
echo ""

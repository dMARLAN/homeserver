#!/bin/bash

set -e

# A dev kind cluster on this machine is the current kubectl context; production must be named.
KUBECTL="${KUBECTL:-kubectl --context homeserver}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CERT_MANAGER_VERSION="v1.18.2"

echo "Installing cert-manager ${CERT_MANAGER_VERSION}..."
${KUBECTL} apply -f "https://github.com/cert-manager/cert-manager/releases/download/${CERT_MANAGER_VERSION}/cert-manager.yaml"

${KUBECTL} rollout status deployment/cert-manager -n cert-manager --timeout=180s
${KUBECTL} rollout status deployment/cert-manager-cainjector -n cert-manager --timeout=180s
${KUBECTL} rollout status deployment/cert-manager-webhook -n cert-manager --timeout=180s

echo "Applying letsencrypt ClusterIssuer..."
# The webhook can reject requests for a short window after its rollout completes.
for attempt in {1..12}; do
    if ${KUBECTL} apply -f "${SCRIPT_DIR}/cluster-issuer.yaml"; then
        echo "cert-manager setup complete."
        exit 0
    fi
    echo "Webhook not ready yet (attempt ${attempt}/12), retrying in 5s..."
    sleep 5
done

echo "Error: failed to apply ClusterIssuer after 12 attempts." >&2
exit 1

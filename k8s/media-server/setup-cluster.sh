#!/bin/bash
# Points kubectl at the homeserver k3s cluster (context "homeserver"), installs
# the nvidia RuntimeClass + device plugin, then deploys the media-server stack.
#
# Run ./setup-host-k3s.sh once (as root) before the first run of this script.
#
#   ./setup-cluster.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K3S_KUBECONFIG="/etc/rancher/k3s/k3s.yaml"

cd "${SCRIPT_DIR}"

if [[ ! -r "${K3S_KUBECONFIG}" ]]; then
    echo "Cannot read ${K3S_KUBECONFIG} — run ./setup-host-k3s.sh first." >&2
    exit 1
fi

mkdir -p "${HOME}/.kube"
sed 's/\bdefault\b/homeserver/g' "${K3S_KUBECONFIG}" > "${HOME}/.kube/config"
chmod 600 "${HOME}/.kube/config"
kubectl config use-context homeserver

echo "Installing nvidia RuntimeClass + device plugin..."
kubectl apply -f jellyfin/nvidia-runtimeclass.yaml
kubectl apply -f gpu/nvidia-device-plugin.yaml

echo "Deploying media-server stack..."
./deploy.sh

#!/bin/bash
# One-time host setup: replaces any previous k3s install with a fresh one for
# the homeserver, backing up the old cluster's PVC storage (photography-server
# postgres) and state first. GPU needs no extra host config: k3s auto-detects
# the nvidia-container-runtime already installed for the RTX 2070.
#
#   sudo ./setup-host-k3s.sh
#
# Idempotent: safe to re-run (each run backs up and reinstalls fresh).

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Must run as root: sudo $0" >&2
    exit 1
fi

BACKUP_DIR="/mnt/media-server/backups"
STAMP="$(date +%Y%m%d-%H%M%S)"

if command -v k3s > /dev/null 2>&1; then
    mkdir -p "${BACKUP_DIR}"
    timeout 20 k3s kubectl get all,pv,pvc -A -o wide \
        > "${BACKUP_DIR}/old-k3s-state-${STAMP}.txt" 2>&1 || true
    if [[ -d /var/lib/rancher/k3s/storage ]]; then
        tar czf "${BACKUP_DIR}/old-k3s-pvc-storage-${STAMP}.tar.gz" -C /var/lib/rancher/k3s storage
        echo "Backed up old PVC storage to ${BACKUP_DIR}/old-k3s-pvc-storage-${STAMP}.tar.gz"
    fi
    echo "Removing old k3s install..."
    /usr/local/bin/k3s-uninstall.sh
fi

mkdir -p /etc/rancher/k3s
cat > /etc/rancher/k3s/config.yaml << 'EOF'
write-kubeconfig-mode: "0644"
EOF

echo "Installing fresh k3s..."
curl -sfL https://get.k3s.io | sh -

NODE="$(hostname | tr '[:upper:]' '[:lower:]')"
for _ in $(seq 1 60); do
    k3s kubectl get "node/${NODE}" > /dev/null 2>&1 && break
    sleep 2
done
k3s kubectl wait --for=condition=Ready "node/${NODE}" --timeout=180s
echo "k3s is up. Now run ./setup-cluster.sh as your normal user."

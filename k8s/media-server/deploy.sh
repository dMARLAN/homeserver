#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "Deploying media server stack..."

# Apply namespace
kubectl apply -f namespace.yaml

# Apply persistent volumes and claims
kubectl apply -f media-storage-pv.yaml
kubectl apply -f jellyfin/pv.yaml
kubectl apply -f prowlarr/pv.yaml
kubectl apply -f radarr/pv.yaml
kubectl apply -f sonarr/pv.yaml
kubectl apply -f jellyseerr/pv.yaml
kubectl apply -f qbittorrent/pv.yaml

# Apply deployments
kubectl apply -f jellyfin/deployment.yaml
kubectl apply -f prowlarr/deployment.yaml
kubectl apply -f radarr/deployment.yaml
kubectl apply -f sonarr/deployment.yaml
kubectl apply -f jellyseerr/deployment.yaml
kubectl apply -f qbittorrent/deployment.yaml
kubectl apply -f flaresolverr/deployment.yaml

# Apply services
kubectl apply -f jellyfin/service.yaml
kubectl apply -f prowlarr/service.yaml
kubectl apply -f radarr/service.yaml
kubectl apply -f sonarr/service.yaml
kubectl apply -f jellyseerr/service.yaml
kubectl apply -f qbittorrent/service.yaml
kubectl apply -f flaresolverr/service.yaml

echo "Media server stack deployed successfully!"
echo ""

NODE_IP=$(tailscale ip 2>/dev/null | head -1)
if [ -z "$NODE_IP" ]; then
    NODE_IP="<your-node-ip>"
    echo "Could not detect node IP automatically. Replace <your-node-ip> with your actual node IP:"
fi

echo "🌐 Service URLs:"
echo "  Jellyfin:             http://${NODE_IP}:30096"
echo "  Jellyseerr (mobile):  http://${NODE_IP}:30055"
echo "  Prowlarr:             http://${NODE_IP}:30696"
echo "  Radarr:               http://${NODE_IP}:30878"
echo "  Sonarr:               http://${NODE_IP}:30989"
echo "  qBittorrent:          http://${NODE_IP}:30080"
echo "  FlareSolverr:         http://${NODE_IP}:30191"
echo ""

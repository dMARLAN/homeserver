.PHONY: deploy up start stop down status logs clean help

deploy-media-server:
	./k8s/media-server/deploy.sh

media-server-up:
	kubectl scale deployment --replicas=1 -n media-server --all
	@echo "✅ All services started"

media-server-down:
	kubectl scale deployment --replicas=0 -n media-server --all
	@echo "✅ All services stopped"

teardown-media-server:
	@echo "🗑️  Deleting media server stack..."
	@echo "⚠️  This will delete all services but preserve data!"
	@read -p "Are you sure? (y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	kubectl delete namespace media-server --grace-period=30
	kubectl get pv -o name | grep -E "(jellyfin|prowlarr|radarr|sonarr|jellyseerr|qbittorrent|shared-media|arr-downloads)" | xargs kubectl delete || true
	@echo "✅ Stack deleted (data preserved in /mnt/media-server/)"

# Get service URLs
media-server-urls:
	@echo "🌐 Service URLs:"
	@echo ""
	@NODE_IP=$$(tailscale ip 2>/dev/null | head -1); \
	if [ -z "$$NODE_IP" ]; then \
		NODE_IP="<your-tailscale-ip>"; \
		echo "⚠️  Could not detect Tailscale IP"; \
	fi; \
	echo "  Jellyfin:             http://$$NODE_IP:30096"; \
	echo "  Jellyseerr:           http://$$NODE_IP:30055"; \
	echo "  Prowlarr:             http://$$NODE_IP:30696"; \
	echo "  Radarr:               http://$$NODE_IP:30878"; \
	echo "  Sonarr:               http://$$NODE_IP:30989"; \
	echo "  qBittorrent:          http://$$NODE_IP:30080"; \
	echo "  FlareSolverr:         http://$$NODE_IP:30191"

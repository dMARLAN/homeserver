.PHONY: \
deploy-media-server media-server-up media-server-down teardown-media-server media-server-urls \
deploy-photography-server photography-server-up photography-server-down teardown-photography-server photography-server-urls

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

# Photography Server targets
deploy-photography-server:
	./k8s/photography-server/deploy.sh

photography-server-up:
	kubectl scale deployment --replicas=1 -n photography-server --all
	@echo "✅ Photography server started"

photography-server-down:
	kubectl scale deployment --replicas=0 -n photography-server --all
	@echo "✅ Photography server stopped"

teardown-photography-server:
	@echo "🗑️  Deleting photography server stack..."
	@echo "⚠️  This will delete all services but preserve data!"
	@read -p "Are you sure? (y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	kubectl delete namespace photography-server --grace-period=30
	kubectl delete pv photos-pv || true
	@echo "✅ Photography server deleted (PostgreSQL data preserved in local storage)"

# Get photography server URLs
photography-server-urls:
	@echo "📷 Photography Server URLs:"
	@echo ""
	@NODE_IP=$$(tailscale ip 2>/dev/null | head -1); \
	if [ -z "$$NODE_IP" ]; then \
		NODE_IP="<your-tailscale-ip>"; \
		echo "⚠️  Could not detect Tailscale IP"; \
	fi; \
	FRONTEND_PORT=$$(kubectl get svc frontend-service -n photography-server -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null); \
	if [ -z "$$FRONTEND_PORT" ]; then \
		echo "  Frontend:             Use 'kubectl port-forward -n photography-server svc/frontend-service 3000:3000'"; \
		echo "  API:                  Use 'kubectl port-forward -n photography-server svc/api-service 8000:8000'"; \
		echo "  Sync Worker Health:   Use 'kubectl port-forward -n photography-server svc/sync-worker-service 8001:8001'"; \
	else \
		echo "  Frontend:             http://$$NODE_IP:$$FRONTEND_PORT"; \
		echo "  API (port-forward):   kubectl port-forward -n photography-server svc/api-service 8000:8000"; \
		echo "  Sync Health:          kubectl port-forward -n photography-server svc/sync-worker-service 8001:8001"; \
	fi

.PHONY: \
deploy-media-server media-server-up media-server-down teardown-media-server media-server-urls

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
	kubectl delete namespace media-server --grace-period=30
	kubectl get pv -o name | grep -E "(jellyfin|prowlarr|radarr|sonarr|jellyseerr|qbittorrent|shared-media|arr-downloads)" | xargs kubectl delete || true
	@echo "✅ Stack deleted (data preserved in /mnt/media-server/)"


.PHONY: \
deploy-media-server media-server-up media-server-down teardown-media-server media-server-urls \
wedding-build deploy-wedding wedding-up wedding-down wedding-migrate teardown-wedding

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

wedding-build:
	@test -n "${WEDDING_REPO}" || { echo "Usage: make wedding-build WEDDING_REPO=/path/to/wedding-website"; exit 1; }
	./k8s/wedding/build-images.sh ${WEDDING_REPO}

deploy-wedding:
	./k8s/wedding/deploy.sh

wedding-up:
	kubectl scale deployment --replicas=1 -n wedding --all
	@echo "✅ Wedding services started"

wedding-down:
	kubectl scale deployment --replicas=0 -n wedding --all
	@echo "✅ Wedding services stopped"

wedding-migrate:
	kubectl delete job wedding-migrate -n wedding --ignore-not-found
	kubectl apply -f k8s/wedding/migrate-job.yaml
	kubectl wait --for=condition=complete job/wedding-migrate -n wedding --timeout=180s
	@echo "✅ Migrations applied"

teardown-wedding:
	@echo "🗑️  Deleting wedding stack..."
	kubectl delete namespace wedding --grace-period=30
	kubectl get pv -o name | grep -E "wedding-(postgres-data|photos)" | xargs kubectl delete || true
	@echo "✅ Stack deleted (data preserved in /mnt/wedding/)"


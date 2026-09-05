# A dev kind cluster on this machine is the current kubectl context; production must be named.
KUBECTL ?= kubectl --context homeserver
WEDDING_REPO ?= ${HOME}/PycharmProjects/wedding-website

.PHONY: \
deploy-media-server media-server-up media-server-down teardown-media-server media-server-urls \
wedding-build wedding-redeploy wedding-restart deploy-wedding wedding-up wedding-down wedding-migrate teardown-wedding

deploy-media-server:
	./k8s/media-server/deploy.sh

media-server-up:
	${KUBECTL} scale deployment --replicas=1 -n media-server --all
	@echo "✅ All services started"

media-server-down:
	${KUBECTL} scale deployment --replicas=0 -n media-server --all
	@echo "✅ All services stopped"

teardown-media-server:
	@echo "🗑️  Deleting media server stack..."
	${KUBECTL} delete namespace media-server --grace-period=30
	${KUBECTL} get pv -o name | grep -E "(jellyfin|prowlarr|radarr|sonarr|jellyseerr|qbittorrent|shared-media|arr-downloads)" | xargs ${KUBECTL} delete || true
	@echo "✅ Stack deleted (data preserved in /mnt/media-server/)"

wedding-build:
	@test -d "${WEDDING_REPO}" || { echo "wedding-website repo not found at ${WEDDING_REPO} (override with WEDDING_REPO=/path)"; exit 1; }
	KUBECTL="${KUBECTL}" ./k8s/wedding/build-images.sh ${WEDDING_REPO}

# Migrate before restarting so the new code never runs against the old schema.
wedding-redeploy:
	git -C ${WEDDING_REPO} pull --ff-only
	$(MAKE) wedding-build
	$(MAKE) wedding-migrate
	$(MAKE) wedding-restart
	@echo "✅ Wedding site redeployed"

wedding-restart:
	${KUBECTL} rollout restart deployment/wedding-api deployment/wedding-frontend deployment/wedding-mail -n wedding
	${KUBECTL} rollout status deployment/wedding-api -n wedding --timeout=180s
	${KUBECTL} rollout status deployment/wedding-frontend -n wedding --timeout=180s
	${KUBECTL} rollout status deployment/wedding-mail -n wedding --timeout=180s
	@echo "✅ Wedding deployments restarted"

deploy-wedding:
	KUBECTL="${KUBECTL}" ./k8s/wedding/deploy.sh

wedding-up:
	${KUBECTL} scale deployment --replicas=1 -n wedding --all
	@echo "✅ Wedding services started"

wedding-down:
	${KUBECTL} scale deployment --replicas=0 -n wedding --all
	@echo "✅ Wedding services stopped"

wedding-migrate:
	${KUBECTL} delete job wedding-migrate -n wedding --ignore-not-found
	${KUBECTL} apply -f k8s/wedding/migrate-job.yaml
	${KUBECTL} wait --for=condition=complete job/wedding-migrate -n wedding --timeout=180s
	@echo "✅ Migrations applied"

teardown-wedding:
	@echo "🗑️  Deleting wedding stack..."
	${KUBECTL} delete namespace wedding --grace-period=30
	${KUBECTL} get pv -o name | grep -E "wedding-(postgres-data|photos|mail-spool|mail-inbox)" | xargs ${KUBECTL} delete || true
	@echo "✅ Stack deleted (data preserved in /mnt/wedding/)"


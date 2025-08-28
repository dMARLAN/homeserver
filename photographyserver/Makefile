DOCKER_COMPOSE_CMD := "./docker_compose/docker-compose.sh"

.PHONY: validate-api validate-db validate-sync validate-frontend \
format \
ci

### Validation targets
validate-api:
	@echo "### Validating API..."
	cd src/pgs_api && uv run make ci
	@echo "### API validation completed successfully\n"

validate-db:
	@echo "### Validating Database..."
	cd src/pgs_db && uv run make ci
	@echo "### Database validation completed successfully\n"

validate-sync:
	@echo "### Validating Sync Worker..."
	cd src/pgs_sync && uv run make ci
	@echo "### Sync Worker validation completed successfully\n"

validate-frontend:
	@echo "### Validating Frontend..."
	cd src/frontend && npm run lint
	@echo "### Frontend validation completed successfully\n"


### Formatting targets
format:
	../scripts/py_format.sh api db sync_worker


### Continuous Integration target
ci: validate-api validate-db validate-sync validate-frontend
	@echo "Done"

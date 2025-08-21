DOCKER_COMPOSE_CMD := "./docker_compose/docker-compose.sh"

.PHONY: build up up-dev down \
validate-foo \
format-foo \
ci


### Docker Compose targets
build:
	$(DOCKER_COMPOSE_CMD) build

up: build
	$(DOCKER_COMPOSE_CMD) up

up-dev: build
	$(DOCKER_COMPOSE_CMD) up --watch

down:
	$(DOCKER_COMPOSE_CMD) down


### Validation targets
validate-foo:
	@echo "### Validating Foo..."
	cd src/foo && uv run make ci
	@echo "### Foo validation completed successfully\n"

### Formatting targets
format-api:
	cd src/foo && uv run make format


### Continuous Integration target
ci: validate-foo
	@echo "Done"

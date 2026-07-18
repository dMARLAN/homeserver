# Wedding Website

Production deployment of [wedding-website](https://github.com/dMARLAN/wedding-website)
(chadandjanina.wedding). That repo builds the images and its `k8s/` manifests mirror
this deployment's shape; this directory holds the production glue.

| Component | Image                                     | Host                        |
|-----------|-------------------------------------------|-----------------------------|
| frontend  | `ghcr.io/dmarlan/wedding-frontend:latest` | chadandjanina.wedding, www. |
| api       | `ghcr.io/dmarlan/wedding-api:latest`      | api.chadandjanina.wedding   |
| postgres  | `postgres:16`                             | cluster-internal only       |

## Prerequisites

1. **DNS** — at Namecheap, create A records for `@`, `www`, and `api` on
   `chadandjanina.wedding`, all pointing at the home network's public IP.
2. **Port forwarding** — forward router ports 80 and 443 to the k3s node (Traefik,
   the k3s default ingress controller, listens on both; 80 is also needed for ACME
   HTTP-01 challenges).
3. **CGNAT caveat** — if the ISP does not hand out a real public IP (CGNAT), port
   forwarding cannot work; use a Cloudflare Tunnel to the two Services instead.
4. **cert-manager** — one-time install (pinned version + `letsencrypt` ClusterIssuer,
   ACME HTTP-01 via Traefik):

   ```
   ./setup-cert-manager.sh
   ```

## Secrets

This repo is public — real secret values are never committed. Copy the example and
fill in real values (the real file is gitignored):

```
cp secrets.example.yaml secrets.yaml
# edit secrets.yaml — deploy.sh applies it
```

Rules the values must follow:

- `ADMIN_AUTH_JWT_SECRET` must be identical in `wedding-frontend-secrets` and
  `wedding-api-secrets`: the frontend mints an HS256 JWT with it and the API
  validates it. Admin auth is a single shared password (`ADMIN_PASSWORD`) — there
  is no Google SSO.
- `DB_PASSWORD` (`wedding-api-secrets`) must equal `POSTGRES_PASSWORD`
  (`wedding-postgres-secrets`) — the same database credential referenced from two
  places.

## Image pull secret (ghcr-pull)

The wedding-website repo is private, so its GHCR packages may be private too. Both
deployments and the migration Job reference `imagePullSecrets: ghcr-pull`. Create it
once with a GitHub PAT that has `read:packages`:

```
kubectl create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username=dMARLAN \
  --docker-password=<github-pat-with-read:packages> \
  -n wedding
```

(Alternatively, make the GHCR packages public and delete the `imagePullSecrets`
blocks.)

## Deploy

```
./deploy.sh          # or: make deploy-wedding (from repo root)
```

The script applies namespace → PVs → secrets → configmap → postgres (waits for
ready) → migration Job (waits for completion) → api → frontend → ingress, then
prints the URLs. It is idempotent — re-run it to roll out changes. Pods pull
`:latest`, so after a new image is published:
`kubectl rollout restart deployment/wedding-api deployment/wedding-frontend -n wedding`.

## Migrations

Run migrations on demand (deploy.sh also runs them on every deploy):

```
make wedding-migrate   # deletes the previous Job, re-applies it, waits for completion
```

The Job runs `alembic upgrade head` from `/app/src/db` inside the api image using
the same DB env as the api.

> **⚠️ Caveat — api image is currently missing the alembic files.** The api image's
> `src/api/dockerfiles/base.Dockerfile` copies `src/db/pyproject.toml` and
> `src/db/src` but **not** `src/db/alembic.ini` or `src/db/alembic/` (env.py +
> versions). The `alembic` package itself is installed (it is a main dependency of
> `wedding-db`), so the Job will work as written once the Dockerfile adds:
>
> ```dockerfile
> COPY ./src/db/alembic.ini ./src/db/alembic.ini
> COPY ./src/db/alembic ./src/db/alembic
> ```
>
> Until that lands in wedding-website and a new image is published, the migration
> Job will fail with "No config file 'alembic.ini' found".

**Never run the seed scripts (`src/db/scripts/seed_dev.py`) against production** —
they exist for local dev fixtures only.

## Backups

`/mnt/wedding/postgres-data` and `/mnt/wedding/photos` on the node are the system
of record (hostPath PVs, `Retain` reclaim policy — they survive `teardown-wedding`).
Recommended: a nightly cron that runs
`kubectl exec deploy/postgres -n wedding -- pg_dump -U postgres wedding` plus an
`rsync` of `/mnt/wedding/photos` to another machine or drive. Not automated here.

## Makefile targets (repo root)

| Target             | What it does                                       |
|--------------------|----------------------------------------------------|
| `deploy-wedding`   | Runs `deploy.sh`                                   |
| `wedding-up`       | Scales all wedding deployments to 1                |
| `wedding-down`     | Scales all wedding deployments to 0                |
| `wedding-migrate`  | Re-runs the migration Job and waits for completion |
| `teardown-wedding` | Deletes the namespace + PVs (host data preserved)  |

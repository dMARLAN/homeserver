# Wedding Website

Production deployment of [wedding-website](https://github.com/dMARLAN/wedding-website)
(chadandjanina.wedding). Images are built directly on this server from a local
checkout of that repo (no container registry); its `k8s/` manifests mirror this
deployment's shape, and this directory holds the production glue.

| Component | Image                                      | Host                        |
|-----------|--------------------------------------------|-----------------------------|
| frontend  | `docker.io/library/wedding-frontend:prod`  | chadandjanina.wedding, www. |
| api       | `docker.io/library/wedding-api:prod`       | api.chadandjanina.wedding   |
| postgres  | `postgres:16`                              | cluster-internal only       |

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

## Build images

Images are built locally with docker and imported into k3s containerd — there is
no registry, and both deployments plus the migration Job use
`imagePullPolicy: Never`.

1. Clone (or `git pull`) the wedding-website repo with your own git credentials,
   e.g. to `/home/marlan/wedding-website`. Scripts never touch git.
2. Build + import:

   ```
   sudo ./build-images.sh /home/marlan/wedding-website
   # or, from repo root: sudo make wedding-build WEDDING_REPO=/home/marlan/wedding-website
   ```

The script builds `wedding-api:prod` (repo-root context,
`src/api/dockerfiles/base.Dockerfile`) and `wedding-frontend:prod`
(`dockerfiles/frontend.Dockerfile` with `src/frontend` as context and
`NEXT_PUBLIC_API_URL=https://api.chadandjanina.wedding` baked in), pipes each
through `docker save` into `k3s ctr -n k8s.io images import -`, and — if the
wedding deployments already exist — restarts them so they pick up the new images.
containerd stores the imported images as `docker.io/library/wedding-*:prod`, which
is what the manifests reference.

## Deploy

```
./deploy.sh          # or: make deploy-wedding (from repo root)
```

The script applies namespace → PVs → secrets → configmap → postgres (waits for
ready) → migration Job (waits for completion) → api → frontend → ingress, then
prints the URLs. It is idempotent — re-run it to roll out changes. After building
new images there is nothing extra to do: `build-images.sh` already runs
`kubectl rollout restart` on both deployments.

## Migrations

Run migrations on demand (deploy.sh also runs them on every deploy):

```
make wedding-migrate   # deletes the previous Job, re-applies it, waits for completion
```

The Job runs `alembic upgrade head` from `/app/src/db` inside the api image using
the same DB env as the api.

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
| `wedding-build`    | Runs `build-images.sh ${WEDDING_REPO}`             |
| `deploy-wedding`   | Runs `deploy.sh`                                   |
| `wedding-up`       | Scales all wedding deployments to 1                |
| `wedding-down`     | Scales all wedding deployments to 0                |
| `wedding-migrate`  | Re-runs the migration Job and waits for completion |
| `teardown-wedding` | Deletes the namespace + PVs (host data preserved)  |

# Wedding Website

Production deployment of [wedding-website](https://github.com/dMARLAN/wedding-website)
(chadandjanina.wedding). That repo builds the images and its `k8s/` manifests mirror
this deployment's shape; this directory holds the production glue.

## Secrets

This repo is public — real secret values are never committed. Copy the example and
fill in real values (the real file is gitignored):

```
cp secrets.example.yaml secrets.yaml
# edit secrets.yaml, then:
kubectl apply -f secrets.yaml
```

Admin auth is a single shared password (`ADMIN_PASSWORD`) — there is no Google SSO.
`ADMIN_AUTH_JWT_SECRET` must be identical in `wedding-frontend-secrets` and
`wedding-api-secrets`: the frontend mints an HS256 JWT with it and the API validates it.

## Still to be added

Deployment manifests (frontend, api, postgres), PVs for Postgres data + uploaded
photos, ingress + TLS for chadandjanina.wedding, and an image pull strategy.

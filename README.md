Welcome to Chad's Home Server!

## Stacks

- **Media server** (`k8s/media-server/`) — Jellyfin + the *arr suite on k3s, exposed
  via NodePorts over Tailscale. Deploy with `make deploy-media-server`.
- **Wedding website** (`k8s/wedding/`) — production deployment of
  [wedding-website](https://github.com/dMARLAN/wedding-website) at
  [chadandjanina.wedding](https://chadandjanina.wedding): Next.js frontend, FastAPI
  api, Postgres, Traefik ingress with cert-manager/Let's Encrypt TLS. Deploy with
  `make deploy-wedding` — see [k8s/wedding/README.md](k8s/wedding/README.md) for
  prerequisites (DNS, port forwarding, secrets, image pull auth).

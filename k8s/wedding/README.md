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
| mail      | `docker.io/library/wedding-mail:prod`      | mail.chadandjanina.wedding (port 25 only) |

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
5. **Mail** — forward router port 25 as well (inbound MX) and ask Shaw to unblock outbound
   TCP/25 + set the PTR; DNS in `mail/DNS.md`.

Every `kubectl` in the scripts and Makefile runs as `${KUBECTL}` (default
`kubectl --context homeserver`): a dev kind cluster on this machine is the *current* context,
so bare `kubectl` would hit the wrong cluster.

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
`src/api/dockerfiles/base.Dockerfile`), `wedding-frontend:prod`
(`dockerfiles/frontend.Dockerfile` with `src/frontend` as context and
`NEXT_PUBLIC_API_URL=https://api.chadandjanina.wedding` baked in) and
`wedding-mail:prod` (`mail/Dockerfile` in this repo), pipes each through
`docker save` into `k3s ctr -n k8s.io images import -`. It does not restart
anything: `make wedding-restart` rolls the deployments, and `make wedding-redeploy`
sequences pull → build → migrate → restart so new code never runs against an old schema.
containerd stores the imported images as `docker.io/library/wedding-*:prod`, which
is what the manifests reference.

## Deploy

```
./deploy.sh          # or: make deploy-wedding (from repo root)
```

The script applies namespace → PVs → secrets → api configmap → postgres (waits for
ready) → migration Job (waits for completion) → mail (configmap, certificate, deployment,
services) → api → frontend → ingress, then prints the URLs. It is idempotent — re-run it
to roll out changes. After building new images, run `make wedding-migrate` and then
`make wedding-restart` (or just `make wedding-redeploy`, which does both).

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
`/mnt/wedding/mail-spool` is the Postfix queue: it only holds mail that is still being
delivered, so it needs no backup, but it is kept on the host so queued mail survives a
pod restart. `/mnt/wedding/mail/inbox` is the received-mail Maildir (`hello@`, `dmarc@`,
`postmaster@`) — back it up with the photos.
`backup/cronjob.yaml` runs nightly at 03:15 America/Winnipeg: a `pg_dump -Fc` of the
database plus a tarball of `/mnt/wedding/photos` and `/mnt/wedding/mail`, written to
`/mnt/wedding/backups` (`backup/pv.yaml`), keeping seven days. Run one on demand with
`kubectl --context homeserver -n wedding create job backup-now --from=cronjob/wedding-backup`.

Restore the database (stops the api first so nothing writes mid-restore):

    kubectl --context homeserver -n wedding scale deployment/wedding-api --replicas=0
    kubectl --context homeserver -n wedding exec -i deploy/postgres -- \
        pg_restore -U postgres -d wedding --clean --if-exists < /mnt/wedding/backups/wedding-db-<stamp>.dump
    kubectl --context homeserver -n wedding scale deployment/wedding-api --replicas=1

The backups sit on the same disk as the data, so copy `/mnt/wedding/backups` off-host
for protection against drive loss.

## Mail (`wedding-mail`)

One pod (`mail/deployment.yaml`) built from `mail/Dockerfile` — Debian, Postfix and OpenDKIM,
configured at boot by `mail/entrypoint.sh` from the env in `mail/configmap.yaml`. It is both the
public MX for `chadandjanina.wedding` and the api's outbound relay.

```
                     internet                                   cluster
                        │                                          │
  MX / port 25 ────► mail-public (LoadBalancer :25) ──► smtpd :25 ─┤  api ──► mail (ClusterIP :587) ──► smtpd :587
                                                             │      │                                       │
                                        reject_unauth_destination   │                       permit_mynetworks, reject
                                        only hello@/dmarc@/postmaster@                       any recipient, DKIM-signed
                                                             │                                              │
                                                /var/mail/vhosts/inbox/  (Maildir)                 remote MXes (TLS may)
                                                = /mnt/wedding/mail/inbox on the node
```

### Two listeners, two trust levels

| Port | Exposed by                                | Who may connect         | Relay rule                                    | Purpose                                                   |
|------|-------------------------------------------|-------------------------|-----------------------------------------------|-----------------------------------------------------------|
| 25   | `mail-public` (LoadBalancer) + `mail`     | anyone                  | `reject_unauth_destination` — never mynetworks | Public MX: accepts mail *for* our three addresses only    |
| 587  | `mail` (ClusterIP) only                   | `MYNETWORKS` (pod/svc CIDRs) | `permit_mynetworks, reject`               | api submission: plaintext, no auth, relays anywhere, signed |

Why two: k3s ServiceLB (klipper) masquerades external connections, so a stranger on port 25 can
show up with a pod-CIDR source address. If port 25 trusted `mynetworks` that would make the
box an open relay. So port 25 grants nothing to any network and only checks the recipient
(`reject_non_fqdn_recipient, reject_unknown_recipient_domain, reject_unlisted_recipient`) and
sender (`reject_non_fqdn_sender, reject_unknown_sender_domain`); the trusting submission
listener exists only on the ClusterIP Service, which nothing outside the cluster can reach.
`mail` also exposes port 25 so `smoke-test.sh` can exercise the public rules from inside the
cluster.

`externalTrafficPolicy: Local` on `mail-public` keeps the client IP where k3s can; it is a
logging nicety, not a security control.

### Inbound flow

`virtual_mailbox_domains = chadandjanina.wedding`; `dmarc@` and `postmaster@` are virtual
aliases of `hello@`, and `hello@` maps to the Maildir `inbox/` under `/var/mail/vhosts`
(uid/gid 5000). Anything else at the domain is rejected at RCPT with
`550 5.1.1 User unknown in virtual mailbox table`, and any other domain with
`554 5.7.1 Relay access denied`. The api pod mounts the same PVC (`mail-inbox-pvc`) at
`/var/mail/vhosts` and reads `MAIL_INBOX_DIR=/var/mail/vhosts/inbox` with `mailbox.Maildir`;
it runs as root so the 0600/uid-5000 files are readable. New messages sit in `inbox/new/`
until a reader moves them to `cur/`.

### Outbound flow

The api connects to `mail:587`, plaintext, no auth (`EMAIL_SMTP_HOST`/`EMAIL_SMTP_PORT` in
`api/configmap.yaml`). OpenDKIM (milter on `127.0.0.1:8891`, `Mode sv`) signs mail from
`InternalHosts` (= `MYNETWORKS`) whose `From:` is `chadandjanina.wedding` with selector
`std2026` (`relaxed/simple`, `OversignHeaders From`), and verifies everything else. Postfix then
delivers straight to the recipient MX with opportunistic TLS (`smtp_tls_security_level = may`,
system CA bundle). The queue is on `/mnt/wedding/mail-spool`, so mail accepted before a pod
restart is still retried afterwards (up to `maximal_queue_lifetime`, 5 days).

If the milter is unreachable, port 25 still accepts (`milter_default_action = accept`, mail is
merely unverified) but port 587 tempfails, so a dead OpenDKIM never sends unsigned campaign
mail.

**Smarthost fallback**: set `RELAYHOST: "[smtp.provider.example]:587"` in `mail/configmap.yaml`
and `RELAYHOST_USERNAME`/`RELAYHOST_PASSWORD` in `wedding-mail-secrets`; the entrypoint adds
`relayhost`, forces `smtp_tls_security_level = encrypt` and enables SASL. DKIM is still ours;
add the provider's `include:` to SPF (`mail/DNS.md`).

### TLS on port 25

`mail/certificate.yaml` is a cert-manager `Certificate` for `mail.chadandjanina.wedding`
(ClusterIssuer `letsencrypt`, HTTP-01 through Traefik using the existing `mail` A record).
The resulting Secret `wedding-mail-tls` is mounted at `/etc/postfix/tls` (`optional: true`).
When `tls.crt`/`tls.key` exist the entrypoint enables STARTTLS (`smtpd_tls_security_level =
may`, `smtpd_tls_chain_files`); when they do not it logs a warning and runs port 25 without
STARTTLS — so the pod also works on first boot before issuance and in the local docker test.
Because the config is rendered at boot, **restart the mail deployment once after the
certificate first becomes Ready** (`kubectl --context homeserver -n wedding rollout restart
deployment/wedding-mail`). Renewals need no restart: each smtpd process re-reads the files
when it starts, and kubelet refreshes the Secret mount within about a minute.

Port 587 is deliberately `smtpd_tls_security_level = none` — it is pod-to-pod only.

### DKIM key

`mail/keys/` is gitignored and holds the private key (`chadandjanina.wedding.private`), the
public PEM, and the ready-to-paste TXT value (`std2026._domainkey.txt`). The private key
reaches the pod as `/etc/opendkim/keys/chadandjanina.wedding.private` — a `secret` volume
(`wedding-mail-secrets`, `defaultMode: 0400`). The entrypoint copies it to
`/run/opendkim/` owned by the `opendkim` user with mode 0400, which is what OpenDKIM's
`RequireSafeKeys` check demands (it stays enabled). To (re)generate the secret YAML to paste
into `secrets.yaml`:

```
kubectl --context homeserver create secret generic wedding-mail-secrets -n wedding \
  --dry-run=client -o yaml \
  --from-file=chadandjanina.wedding.private=mail/keys/chadandjanina.wedding.private
```

If the key is ever rotated, use a **new selector** (bump `DKIM_SELECTOR` and publish a new
`<selector>._domainkey` TXT), and keep the old TXT for a week so in-flight mail still verifies.

### Operating it

```
K="kubectl --context homeserver -n wedding"

# queue: what is waiting / deferred and why
$K exec deploy/wedding-mail -- postqueue -p        # same as: mailq
$K exec deploy/wedding-mail -- postqueue -f        # flush: retry everything now
$K exec deploy/wedding-mail -- postcat -q <id>     # show a queued message (headers + body)
$K exec deploy/wedding-mail -- postsuper -d ALL    # drop the whole queue (careful)

# logs: Postfix and OpenDKIM both go to stdout; every message is traced by queue id
$K logs deploy/wedding-mail -f
$K logs deploy/wedding-mail | grep <queue-id>

# effective Postfix config as the entrypoint rendered it
$K exec deploy/wedding-mail -- postconf -n
$K exec deploy/wedding-mail -- cat /etc/postfix/master.cf

# inbox
$K exec deploy/wedding-mail -- ls -l /var/mail/vhosts/inbox/new
$K get certificate wedding-mail-tls                 # READY=True once issued
$K get svc mail-public                              # EXTERNAL-IP = node IP once ServiceLB is up
```

Deferred mail with `Connection timed out` on port 25 to every MX means the ISP block is still
in place. `status=sent (250 ...)` from the remote MX is the success line.
`DKIM-Signature field added (s=std2026, d=chadandjanina.wedding)` in the log is OpenDKIM
confirming it signed.

### Testing

`mail/smoke-test.sh you@example.com` runs two one-off `python:3.12-alpine` pods: one sends
`you@example.com → hello@chadandjanina.wedding` through `mail:25` (public-MX rules) and the
script checks that a file appears in `/var/mail/vhosts/inbox/new`; the other sends
`hello@ → you@example.com` through `mail:587` and prints the queue. For a raw SMTP session:

```
kubectl --context homeserver run -n wedding -it --rm smtp-debug --image=alpine -- \
  sh -c 'apk add -q busybox-extras && telnet mail 25'
EHLO test
MAIL FROM:<you@example.com>
RCPT TO:<hello@chadandjanina.wedding>      # 250 — accepted for local delivery
RCPT TO:<nobody@chadandjanina.wedding>     # 550 5.1.1 User unknown in virtual mailbox table
RCPT TO:<someone@gmail.com>                # 554 5.7.1 Relay access denied
QUIT
```

The same image can be exercised without the cluster: `docker build -t wedding-mail:prod mail`,
then `docker run` it with the DKIM key mounted at `/etc/opendkim/keys/chadandjanina.wedding.private`,
`MYNETWORKS=127.0.0.0/8,172.16.0.0/12` and ports published on localhost.

### MX cutover (Tuesday, after Shaw)

Do these in order; the site keeps sending regardless — only *receiving* moves.

1. Shaw confirms outbound TCP/25 is open and the PTR is set: `dig +short -x 50.72.88.183` →
   `mail.chadandjanina.wedding.`
2. Forward router TCP/25 to the k3s node; `kubectl --context homeserver -n wedding get svc
   mail-public` shows an `EXTERNAL-IP`.
3. From outside (phone on mobile data): `nc -vz 50.72.88.183 25` answers
   `220 mail.chadandjanina.wedding ESMTP`.
4. `mail/smoke-test.sh you@example.com` passes both halves and the outbound copy lands in your
   inbox with `DKIM: PASS`.
5. Namecheap: Mail Settings → **Custom MX**, add `@ → 10 mail.chadandjanina.wedding`
   (`mail/DNS.md`). This deletes the Namecheap forwarding rules.
6. Send from Gmail to `hello@chadandjanina.wedding`; it must show up in
   `/var/mail/vhosts/inbox/new` within a minute (MX TTL permitting).
7. Remove `include:spf.efwd.registrar-servers.com` from the SPF record.

### Deliverability checklist (after DNS in `mail/DNS.md` has propagated)

1. `dig +short -x 50.72.88.183` → `mail.chadandjanina.wedding.`
2. `dig +short TXT std2026._domainkey.chadandjanina.wedding` returns the DKIM record;
   `dig +short TXT chadandjanina.wedding` shows exactly one `v=spf1` record.
3. Send a test to a Gmail account, open **Show original**: `SPF: PASS`, `DKIM: PASS` with
   `chadandjanina.wedding`, `DMARC: PASS`. Both SPF and DKIM must be *aligned* with the
   `From:` domain — the api sets `From:` and `Message-ID` to `chadandjanina.wedding` for
   this reason.
4. Send a test to the address shown on <https://www.mail-tester.com> and aim for 10/10;
   it also flags a missing PTR, HELO/PTR mismatches and a missing STARTTLS certificate.
5. `kubectl --context homeserver -n wedding get certificate wedding-mail-tls` is `READY=True`
   and the mail pod was restarted after it became so (log shows no "tls.crt or tls.key missing"
   warning).
6. Keep the api's `EMAIL_SEND_DELAY_SECONDS` (default 1s) for the ~200-message send: a
   brand-new residential IP has no reputation, and Gmail rate-limits unknown senders.
7. Once reports at `dmarc@chadandjanina.wedding` (in the shared inbox) look clean, move DMARC
   from `p=none` to `p=quarantine`.

## Makefile targets (repo root)

| Target             | What it does                                       |
|--------------------|----------------------------------------------------|
| `wedding-build`    | Runs `build-images.sh ${WEDDING_REPO}`             |
| `deploy-wedding`   | Runs `deploy.sh`                                   |
| `wedding-up`       | Scales all wedding deployments to 1                |
| `wedding-down`     | Scales all wedding deployments to 0                |
| `wedding-migrate`  | Re-runs the migration Job and waits for completion |
| `teardown-wedding` | Deletes the namespace + PVs (host data preserved)  |

All targets honour `KUBECTL` (default `kubectl --context homeserver`).

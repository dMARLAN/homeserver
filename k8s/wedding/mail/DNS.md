# DNS records for mail (chadandjanina.wedding)

Publish these at Namecheap (Advanced DNS). Namecheap's **Host** field takes the label only —
never the domain: use `@` for the apex, `mail` (not `mail.chadandjanina.wedding`),
`std2026._domainkey`, `_dmarc`.

| Type | Host                 | Value                                                                  | TTL       | Status                              |
|------|----------------------|------------------------------------------------------------------------|-----------|-------------------------------------|
| A    | `mail`               | `50.72.88.183`                                                         | Automatic | published                           |
| MX   | `@`                  | `10 mail.chadandjanina.wedding`                                        | Automatic | **Tuesday, after Shaw** (see below) |
| TXT  | `@`                  | `v=spf1 ip4:50.72.88.183 include:spf.efwd.registrar-servers.com -all`  | Automatic | published                           |
| TXT  | `std2026._domainkey` | see **DKIM** below (one long string)                                   | Automatic | published                           |
| TXT  | `_dmarc`             | `v=DMARC1; p=none; rua=mailto:dmarc@chadandjanina.wedding; fo=1`       | Automatic | published                           |

## MX (inbound) — Tuesday, after Shaw

Inbound mail for `hello@`, `dmarc@` and `postmaster@` is delivered by the `wedding-mail` pod
itself (port 25 via the `mail-public` LoadBalancer Service). Cut over only once Shaw has lifted
the TCP/25 block and set the PTR, and `mail/smoke-test.sh` passes:

1. In Namecheap **Domain → Mail Settings**, switch from **Email Forwarding** to **Custom MX**.
   This removes the `eforward*.registrar-servers.com` MX records and the forwarding rules —
   Namecheap does not allow forwarding and custom MX at the same time.
2. Add the single MX record above (`@` → `10 mail.chadandjanina.wedding`).
3. Forward router TCP/25 to the k3s node, like 80/443.
4. Verify: `dig +short MX chadandjanina.wedding` returns only `10 mail.chadandjanina.wedding.`,
   then send a message from a Gmail account to `hello@chadandjanina.wedding` and check
   `/mnt/wedding/mail/inbox/new` on the node (or the admin inbox in the site).

Once forwarding is gone, drop `include:spf.efwd.registrar-servers.com` from the SPF record —
it only existed so that forwarded mail passed SPF.

## SPF

A domain may have **only one** SPF TXT record — edit the existing one instead of adding a
second. `ip4:50.72.88.183` authorises direct delivery from the home IP. If the smarthost
fallback (`RELAYHOST` in `configmap.yaml`) is ever used, mail leaves from the provider's IPs, so
add the provider's include (e.g. `include:_spf.provider.example`) alongside the `ip4:` term.

## DKIM (`std2026._domainkey`)

Selector `std2026`, RSA-2048. The public half of `keys/chadandjanina.wedding.private`
(regenerate the value with `openssl pkey -in keys/chadandjanina.wedding.private -pubout`,
strip the PEM header/footer and newlines):

```
v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv1ExxbMf8xJVLR2qUTTFY/tpCI0Sv8qAMftyn6dXXJQl8u9A8E3IDPyCuIMSoflf3ztDgvMT0RRiJlAHYUrm+1M0MsXVS/8t3NRm9gIohWVRcfTYVQvxVzGmIHtVnDCz/MttTNWcftjpBX5zIyKxnRPMNwV7Em42IY0cfkjdrWqgc6sWnPMWJ2RzglIpBgSNR6tsPGZdybyFMG4DemtqsGUQzd+gm+6lJWipf28kN+CLHSa9D5E6CSVEP9ztPRx/93Da9W9AnLLRwdsVOiXTEBJf8/dONvbuijiRwJ2EyvTS8oGjJ23Stc1WW5Kqvi0pOM+Yq4uMBGQb4AXsHrU+XQIDAQAB
```

Namecheap accepts the full string in one TXT value (it splits >255-char strings itself).
Verify after propagation:

```
dig +short TXT std2026._domainkey.chadandjanina.wedding
```

DKIM is signed on our side before the message leaves, so a smarthost provider's own DKIM (if
any) is additional, not a replacement.

## DMARC

`p=none` only asks receivers to report; tighten to `p=quarantine` once Gmail "Show original"
consistently shows `SPF: PASS`, `DKIM: PASS` and `DMARC: PASS` with alignment on
`chadandjanina.wedding`. Aggregate reports go to `dmarc@chadandjanina.wedding`, which the mail
pod folds into the shared `hello@` inbox.

## PTR (reverse DNS) — Shaw, not Namecheap

Most large receivers reject or spam-fold mail from IPs whose reverse DNS does not match the
HELO name, and many refuse to talk to an IP with a generic residential PTR at all. Ask Shaw to:

1. lift the outbound TCP/25 block on 50.72.88.183, and
2. set the PTR for `50.72.88.183` to `mail.chadandjanina.wedding`
   (currently `S0106fc777bad0283.wp.shawcable.net`).

Check with `dig +short -x 50.72.88.183`.

## TLS certificate

`certificate.yaml` asks cert-manager for a Let's Encrypt certificate for
`mail.chadandjanina.wedding` (HTTP-01 through Traefik, so it needs only the existing A record and
port 80). No DNS change is required for it.

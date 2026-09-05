#!/bin/bash

set -euo pipefail

usage() {
    echo "Usage: ${0} <you@example.com> [--context <kube-context>]" >&2
    echo "Inbound: sends <you@example.com> -> hello@chadandjanina.wedding through the in-cluster 'mail' Service" >&2
    echo "         on port 25 (public-MX rules) and checks the Maildir." >&2
    echo "Outbound: sends hello@chadandjanina.wedding -> <you@example.com> through 'mail' port 587 and prints the queue." >&2
    exit 1
}

recipient=""
context="homeserver"
while [ $# -gt 0 ]; do
    case "${1}" in
        --context)
            [ $# -ge 2 ] || usage
            context="${2}"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            [ -z "${recipient}" ] || usage
            recipient="${1}"
            shift
            ;;
    esac
done
[ -n "${recipient}" ] || usage

inbox_new="/var/mail/vhosts/inbox/new"

# The Message-ID domain is set explicitly for the same reason the api does it: the default
# would be the pod hostname, which receivers penalise.
read -r -d '' send_script <<'PY' || true
import os
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr

message = EmailMessage()
message["From"] = os.environ["MAIL_FROM"]
message["To"] = os.environ["MAIL_TO"]
message["Subject"] = os.environ["MAIL_SUBJECT"]
message["Date"] = formatdate(localtime=True)
message["Message-ID"] = make_msgid(domain=parseaddr(os.environ["MAIL_FROM"])[1].rsplit("@", 1)[-1])
message.set_content(os.environ["MAIL_BODY"])

with smtplib.SMTP("mail", int(os.environ["MAIL_PORT"]), timeout=30) as smtp:
    smtp.set_debuglevel(1)
    smtp.send_message(message)
PY

send_mail() {
    local port="${1}" mail_from="${2}" mail_to="${3}" subject="${4}" body="${5}"
    kubectl --context "${context}" -n wedding run "mail-smoke-$(date +%s)" \
        --image=python:3.12-alpine \
        --restart=Never \
        --rm \
        --attach \
        --quiet \
        --env="MAIL_PORT=${port}" \
        --env="MAIL_FROM=${mail_from}" \
        --env="MAIL_TO=${mail_to}" \
        --env="MAIL_SUBJECT=${subject}" \
        --env="MAIL_BODY=${body}" \
        -- python3 -c "${send_script}"
}

count_inbox() {
    kubectl --context "${context}" -n wedding exec deploy/wedding-mail -- sh -c "ls ${inbox_new} | wc -l"
}

echo "==> Inbound: ${recipient} -> hello@chadandjanina.wedding via mail:25 (context ${context})..."
before="$(count_inbox)"
after="${before}"
send_mail 25 "${recipient}" "hello@chadandjanina.wedding" "wedding-mail inbound smoke test" \
    "If this file is in ${inbox_new}, the public-MX listener accepted and delivered a message."
for _ in $(seq 1 20); do
    after="$(count_inbox)"
    [ "${after}" -gt "${before}" ] && break
    sleep 1
done
if [ "${after}" -gt "${before}" ]; then
    echo "==> Delivered: ${inbox_new} went from ${before} to ${after} message(s):"
    kubectl --context "${context}" -n wedding exec deploy/wedding-mail -- ls -l "${inbox_new}"
else
    echo "==> FAILED: no new file in ${inbox_new} after 20s; check: kubectl --context ${context} -n wedding logs deploy/wedding-mail" >&2
    exit 1
fi

echo "==> Outbound: hello@chadandjanina.wedding -> ${recipient} via mail:587..."
send_mail 587 "Janina & Chad <hello@chadandjanina.wedding>" "${recipient}" "wedding-mail outbound smoke test" \
    "If you can read this, the submission listener accepted, DKIM-signed and delivered a message. Check SPF/DKIM/DMARC in the received headers."

echo "==> Accepted. Delivery status (empty queue = already handed to the remote MX):"
kubectl --context "${context}" -n wedding exec deploy/wedding-mail -- postqueue -p

#!/bin/bash

set -euo pipefail

MAIL_DOMAIN="${MAIL_DOMAIN:-chadandjanina.wedding}"
MAIL_HOSTNAME="${MAIL_HOSTNAME:-mail.${MAIL_DOMAIN}}"
# Comma-separated lists; Postfix takes them as-is, OpenDKIM needs one entry per line.
MYNETWORKS="${MYNETWORKS:-127.0.0.0/8,10.42.0.0/16,10.43.0.0/16}"
INBOX_ADDRESS="${INBOX_ADDRESS:-hello}"
INBOX_ALIASES="${INBOX_ALIASES:-dmarc,postmaster}"
MESSAGE_SIZE_LIMIT="${MESSAGE_SIZE_LIMIT:-26214400}"
DKIM_SELECTOR="${DKIM_SELECTOR:-std2026}"
DKIM_KEY_FILE="${DKIM_KEY_FILE:-/etc/opendkim/keys/${MAIL_DOMAIN}.private}"
RELAYHOST="${RELAYHOST:-}"
RELAYHOST_USERNAME="${RELAYHOST_USERNAME:-}"
RELAYHOST_PASSWORD="${RELAYHOST_PASSWORD:-}"

TLS_DIR="/etc/postfix/tls"
INBOX_DIR="/var/mail/vhosts/inbox"
INBOX_UID=5000
INBOX_GID=5000
OPENDKIM_RUNTIME_DIR="/run/opendkim"
# Same endpoint, but Postfix and OpenDKIM spell inet sockets differently.
OPENDKIM_LISTEN_SOCKET="inet:8891@127.0.0.1"
POSTFIX_MILTER_SOCKET="inet:127.0.0.1:8891"

log() {
    echo "entrypoint: ${*}" >&2
}

render_main_cf() {
    cat > /etc/postfix/main.cf <<EOF
compatibility_level = 3.6
maillog_file = /dev/stdout

myhostname = ${MAIL_HOSTNAME}
mydomain = ${MAIL_DOMAIN}
myorigin = \$mydomain
smtpd_banner = \$myhostname ESMTP
inet_protocols = ipv4
inet_interfaces = all
mynetworks = ${MYNETWORKS}
message_size_limit = ${MESSAGE_SIZE_LIMIT}
biff = no
append_dot_mydomain = no

# No local(8) delivery at all: every accepted domain is a virtual mailbox domain.
mydestination =
alias_maps =
alias_database =
local_recipient_maps =
local_transport = error:5.1.1 local delivery is disabled on this host

virtual_mailbox_domains = ${MAIL_DOMAIN}
virtual_mailbox_base = /var/mail/vhosts
virtual_mailbox_maps = texthash:/etc/postfix/virtual_mailbox
virtual_alias_maps = texthash:/etc/postfix/virtual_alias
virtual_uid_maps = static:${INBOX_UID}
virtual_gid_maps = static:${INBOX_GID}
virtual_minimum_uid = 100

# Port 25 is the public MX. k3s ServiceLB can SNAT external clients to a pod-CIDR address, so
# permit_mynetworks must never appear here; only the submission listener in master.cf trusts
# mynetworks.
smtpd_relay_restrictions = reject_unauth_destination
smtpd_recipient_restrictions = reject_non_fqdn_recipient, reject_unknown_recipient_domain, reject_unlisted_recipient, permit
smtpd_sender_restrictions = reject_non_fqdn_sender, reject_unknown_sender_domain
smtpd_helo_required = yes
disable_vrfy_command = yes

smtp_tls_security_level = may
smtp_tls_CApath = /etc/ssl/certs
smtp_tls_loglevel = 1
smtpd_tls_loglevel = 1
smtpd_tls_received_header = yes

smtpd_milters = ${POSTFIX_MILTER_SOCKET}
non_smtpd_milters = \$smtpd_milters
milter_protocol = 6
milter_default_action = accept
EOF
}

render_inbound_tls() {
    if [ -s "${TLS_DIR}/tls.crt" ] && [ -s "${TLS_DIR}/tls.key" ]; then
        cat >> /etc/postfix/main.cf <<EOF
smtpd_tls_security_level = may
smtpd_tls_chain_files = ${TLS_DIR}/tls.key, ${TLS_DIR}/tls.crt
EOF
    else
        log "WARNING: ${TLS_DIR}/tls.crt or tls.key missing; port 25 runs without STARTTLS until the certificate exists"
        echo "smtpd_tls_security_level = none" >> /etc/postfix/main.cf
    fi
}

render_relayhost() {
    [ -n "${RELAYHOST}" ] || return 0
    log "relaying all outbound mail through ${RELAYHOST}"
    cat >> /etc/postfix/main.cf <<EOF
relayhost = ${RELAYHOST}
smtp_tls_security_level = encrypt
EOF
    if [ -n "${RELAYHOST_USERNAME}" ] && [ -n "${RELAYHOST_PASSWORD}" ]; then
        (
            umask 077
            echo "${RELAYHOST} ${RELAYHOST_USERNAME}:${RELAYHOST_PASSWORD}" > /etc/postfix/sasl_passwd
        )
        cat >> /etc/postfix/main.cf <<EOF
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = texthash:/etc/postfix/sasl_passwd
smtp_sasl_security_options = noanonymous
EOF
    fi
}

render_master_cf() {
    # Nothing is chrooted: the spool is a hostPath volume and a chroot would need /etc/resolv.conf
    # and the CA bundle copied into it on every boot.
    cat > /etc/postfix/master.cf <<'EOF'
# service   type  private unpriv chroot wakeup maxproc command + args
smtp        inet  n       -      n      -      -       smtpd
submission  inet  n       -      n      -      -       smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=none
  -o smtpd_client_restrictions=permit_mynetworks,reject
  -o smtpd_relay_restrictions=permit_mynetworks,reject
  -o smtpd_recipient_restrictions=permit_mynetworks,reject
  -o smtpd_sender_restrictions=
  -o milter_default_action=tempfail
pickup      unix  n       -      n      60     1       pickup
cleanup     unix  n       -      n      -      0       cleanup
qmgr        unix  n       -      n      300    1       qmgr
tlsmgr      unix  -       -      n      1000?  1       tlsmgr
rewrite     unix  -       -      n      -      -       trivial-rewrite
bounce      unix  -       -      n      -      0       bounce
defer       unix  -       -      n      -      0       bounce
trace       unix  -       -      n      -      0       bounce
verify      unix  -       -      n      -      1       verify
flush       unix  n       -      n      1000?  0       flush
proxymap    unix  -       -      n      -      -       proxymap
proxywrite  unix  -       -      n      -      1       proxymap
smtp        unix  -       -      n      -      -       smtp
relay       unix  -       -      n      -      -       smtp
  -o syslog_name=postfix/relay
showq       unix  n       -      n      -      -       showq
error       unix  -       -      n      -      -       error
retry       unix  -       -      n      -      -       error
discard     unix  -       -      n      -      -       discard
local       unix  -       n      n      -      -       local
virtual     unix  -       n      n      -      -       virtual
lmtp        unix  -       -      n      -      -       lmtp
anvil       unix  -       -      n      -      1       anvil
scache      unix  -       -      n      -      1       scache
postlog     unix-dgram n  -      n      -      1       postlogd
EOF
}

render_virtual_maps() {
    local inbox="${INBOX_ADDRESS}@${MAIL_DOMAIN}"
    local alias
    # The trailing slash makes virtual(8) deliver in Maildir format instead of mbox.
    echo "${inbox} inbox/" > /etc/postfix/virtual_mailbox
    : > /etc/postfix/virtual_alias
    for alias in ${INBOX_ALIASES//,/ }; do
        echo "${alias}@${MAIL_DOMAIN} ${inbox}" >> /etc/postfix/virtual_alias
    done
}

prepare_inbox() {
    mkdir -p "${INBOX_DIR}/new" "${INBOX_DIR}/cur" "${INBOX_DIR}/tmp"
    chown -R "${INBOX_UID}:${INBOX_GID}" /var/mail/vhosts
}

render_opendkim() {
    local network
    mkdir -p "${OPENDKIM_RUNTIME_DIR}"
    : > "${OPENDKIM_RUNTIME_DIR}/TrustedHosts"
    for network in 127.0.0.1 ::1 ${MYNETWORKS//,/ }; do
        echo "${network}" >> "${OPENDKIM_RUNTIME_DIR}/TrustedHosts"
    done
    cat > /etc/opendkim.conf <<EOF
Syslog yes
SyslogSuccess yes
LogWhy yes
UserID opendkim
PidFile ${OPENDKIM_RUNTIME_DIR}/opendkim.pid
Socket ${OPENDKIM_LISTEN_SOCKET}
Mode sv
Canonicalization relaxed/simple
OversignHeaders From
SubDomains no
Domain ${MAIL_DOMAIN}
Selector ${DKIM_SELECTOR}
KeyFile ${OPENDKIM_RUNTIME_DIR}/${MAIL_DOMAIN}.private
InternalHosts ${OPENDKIM_RUNTIME_DIR}/TrustedHosts
EOF
}

install_dkim_key() {
    if [ ! -s "${DKIM_KEY_FILE}" ]; then
        log "ERROR: DKIM key ${DKIM_KEY_FILE} is missing or empty"
        exit 1
    fi
    # Secret mounts are root-owned and read-only, which OpenDKIM's RequireSafeKeys rejects; a
    # private copy owned by the opendkim user satisfies the check instead of disabling it.
    install -o opendkim -g opendkim -m 0400 "${DKIM_KEY_FILE}" "${OPENDKIM_RUNTIME_DIR}/${MAIL_DOMAIN}.private"
}

start_background_services() {
    # OpenDKIM only logs through syslog; busybox syslogd forwards that to the container's stdout.
    busybox syslogd -n -O /dev/stdout &
    opendkim -f -x /etc/opendkim.conf &
}

render_main_cf
render_inbound_tls
render_relayhost
render_master_cf
render_virtual_maps
prepare_inbox
render_opendkim
install_dkim_key

postfix check
start_background_services

exec postfix start-fg

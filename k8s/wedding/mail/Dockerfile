FROM debian:bookworm-slim

# "No configuration" keeps the package from writing a main.cf/master.cf we would overwrite anyway.
RUN set -eux; \
    echo "postfix postfix/main_mailer_type select No configuration" | debconf-set-selections; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        postfix \
        libsasl2-modules \
        opendkim \
        opendkim-tools \
        ca-certificates \
        busybox; \
    rm -rf /var/lib/apt/lists/* /etc/postfix/main.cf /etc/postfix/master.cf

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 25 587

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

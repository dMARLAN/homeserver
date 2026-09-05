#!/bin/bash

set -euo pipefail

BACKUP_DIR="/backups"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
stamp="$(date -u +%Y-%m-%d-%H%M%S)"

dump="${BACKUP_DIR}/wedding-db-${stamp}.dump"
photos="${BACKUP_DIR}/wedding-files-${stamp}.tar.gz"

echo "==> pg_dump -> ${dump}"
pg_dump -h "${PGHOST}" -U "${PGUSER}" -Fc "${PGDATABASE}" > "${dump}.partial"
mv "${dump}.partial" "${dump}"

echo "==> photos + inbox -> ${photos}"
tar -czf "${photos}.partial" -C /data photos mail
mv "${photos}.partial" "${photos}"

echo "==> pruning backups older than ${RETENTION_DAYS} days"
find "${BACKUP_DIR}" -maxdepth 1 -name 'wedding-*' -mtime "+${RETENTION_DAYS}" -print -delete

ls -lh "${BACKUP_DIR}"

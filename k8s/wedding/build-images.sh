#!/bin/bash

set -e

# A dev kind cluster on this machine is the current kubectl context; production must be named.
KUBECTL="${KUBECTL:-kubectl --context homeserver}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    echo "Usage: ${0} <wedding-website-repo-dir>" >&2
    echo "Builds the wedding images from a local wedding-website checkout and imports them into k3s." >&2
    echo "Does not restart anything; run 'make wedding-restart' (after migrations) to roll the new images out." >&2
    exit 1
}

repo_dir="${1:-}"
if [ -z "${repo_dir}" ]; then
    echo "Error: missing wedding-website repo directory argument." >&2
    usage
fi
if [ ! -e "${repo_dir}/.git" ]; then
    echo "Error: ${repo_dir} is not a git checkout of wedding-website." >&2
    usage
fi

# Build from the committed tree, not the working copy: the checkout doubles as a dev
# workspace and can hold half-finished edits when a deploy is kicked off.
export_dir="$(mktemp -d)"
trap 'rm -rf "${export_dir}"' EXIT
git -C "${repo_dir}" archive HEAD | tar -x -C "${export_dir}"
echo "==> Building from $(git -C "${repo_dir}" rev-parse --short HEAD) ($(git -C "${repo_dir}" log -1 --format=%s))"
cd "${export_dir}"

echo "==> Building wedding-api:prod..."
docker build -f src/api/dockerfiles/base.Dockerfile -t wedding-api:prod .

echo "==> Building wedding-frontend:prod..."
docker build -f dockerfiles/frontend.Dockerfile \
    --build-arg NEXT_PUBLIC_API_URL=https://api.chadandjanina.wedding \
    -t wedding-frontend:prod src/frontend

echo "==> Building wedding-mail:prod..."
docker build -t wedding-mail:prod "${SCRIPT_DIR}/mail"

echo "==> Importing wedding-api:prod into k3s containerd..."
docker save wedding-api:prod | sudo k3s ctr -n k8s.io images import -

echo "==> Importing wedding-frontend:prod into k3s containerd..."
docker save wedding-frontend:prod | sudo k3s ctr -n k8s.io images import -

echo "==> Importing wedding-mail:prod into k3s containerd..."
docker save wedding-mail:prod | sudo k3s ctr -n k8s.io images import -


echo "✅ Images built and imported"

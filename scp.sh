SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_TARGET="${DEPLOY_TARGET:?Set DEPLOY_TARGET to user@host:/path before running (e.g. DEPLOY_TARGET=deploy@10.0.0.5:/opt/k9x-studio/ ./scp.sh)}"
scp "$SCRIPT_DIR/k9x_studio.tar.gz" "$DEPLOY_TARGET"

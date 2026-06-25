#!/bin/bash
# Package k9x_studio for deployment — includes Dockerfile + k9-aif-framework templates
#
# studiox replaces studio in place (same pod/container/image names — see
# deployment/k9x-ecosystem-pod.sh and rhel_r820_deploy_studio.sh), so the
# archive renames k9x_studio -> k9x_studio internally. That keeps the
# existing Dockerfile COPY paths and remote deploy script working unchanged.
set -e


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT="$(dirname "$SCRIPT_DIR")"

tar -czf "$SCRIPT_DIR/k9x_studio.tar.gz" \
  -C "$PARENT" \
  --exclude="k9x_studio/.venv" \
  --exclude="k9x_studio/frontend/node_modules" \
  --exclude="k9x_studio/**/__pycache__" \
  --exclude="k9x_studio/.git" \
  --exclude="k9x_studio/k9x_studio.tar.gz" \
  --exclude="k9-aif-framework/.venv" \
  --exclude="k9-aif-framework/**/__pycache__" \
  --exclude="k9-aif-framework/.git" \
  -s '/^k9x_studio/k9x_studio/' \
  k9x_studio \
  deployment/Dockerfile \
  k9-aif-framework/generator/templates

echo "Done → $SCRIPT_DIR/k9x_studio.tar.gz ($(du -sh "$SCRIPT_DIR/k9x_studio.tar.gz" | cut -f1))"

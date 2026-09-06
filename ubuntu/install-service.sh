#!/usr/bin/env bash
# Run this script on the Podman host (as root or with sudo) to install
# and enable the k9-studio-pod systemd service.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/k9-studio-pod.service"
TARGET="/etc/systemd/system/k9-studio-pod.service"

echo "Installing k9-studio-pod.service ..."
cp "$SERVICE_FILE" "$TARGET"
chmod 644 "$TARGET"

systemctl daemon-reload
systemctl enable k9-studio-pod.service
systemctl start  k9-studio-pod.service

echo ""
systemctl status k9-studio-pod.service --no-pager
echo ""
echo "Done. k9-studio-pod will now auto-start on every boot."

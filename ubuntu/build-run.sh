#!/usr/bin/env bash
# k9x_studio — Podman build and deploy helper
# Run from any directory on the Podman host (no sudo needed — script handles it).
#
# Commands:
#   build   — build the k9x-studio container image
#   up      — deploy k9-studio-pod (1 container)
#   down    — stop and remove the pod
#   status  — show pod and container status
#   logs    — tail app-backend logs
#   all     — build + up in one step

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE="k9x-studio:latest"
POD_NAME="k9-studio-pod"

cmd="${1:-help}"

case "$cmd" in

  build)
    echo "Building $IMAGE ..."
    cd "$PROJECT_DIR"
    sudo podman build -t "$IMAGE" -f ubuntu/Containerfile .
    echo "Build complete: $IMAGE"
    ;;

  up)
    echo "Deploying pod: $POD_NAME (1 container) ..."
    sudo podman play kube "$SCRIPT_DIR/studio-pod.yaml" --replace
    echo ""
    echo "Pod running. Containers:"
    sudo podman ps --filter "pod=$POD_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Command}}"
    echo ""
    HOST_IP=$(hostname -I | awk '{print $1}')
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  k9x_studio"
    echo "  Web UI:  http://${HOST_IP}:8090/"
    echo "  Health:  http://${HOST_IP}:8090/api/health"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Logs:"
    echo "  sudo podman logs -f ${POD_NAME}-app-backend"
    ;;

  down)
    echo "Stopping pod: $POD_NAME ..."
    sudo podman play kube "$SCRIPT_DIR/studio-pod.yaml" --down || true
    echo "Pod stopped."
    ;;

  status)
    echo "=== Pod ==="
    sudo podman pod ps --filter "name=$POD_NAME"
    echo ""
    echo "=== Containers ==="
    sudo podman ps -a --filter "pod=$POD_NAME" \
      --format "table {{.Names}}\t{{.Status}}\t{{.RestartCount}}\t{{.Command}}"
    ;;

  logs)
    sudo podman logs -f "${POD_NAME}-app-backend"
    ;;

  all)
    "$0" build
    "$0" up
    ;;

  help|*)
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  build   — build the Podman image ($IMAGE)"
    echo "  up      — deploy $POD_NAME (1 container)"
    echo "  down    — stop and remove the pod"
    echo "  status  — show pod and container status"
    echo "  logs    — tail app-backend logs"
    echo "  all     — build + up in one step"
    ;;

esac

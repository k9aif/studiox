#!/usr/bin/env bash
# k9x_studio — build and run helper (single container, no pod needed)
# Run from any directory on the Podman host (no sudo needed — script handles it).
#
# Commands:
#   build   — build the k9x-studio container image
#   start   — start the container (port 8081)
#   stop    — stop the container
#   logs    — tail logs
#   all     — build + start

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Build context is this project's own directory -- the Containerfile only
# ever copies from ${STUDIO_DIR} (this project itself, including its own
# k9x/_generator_templates/), nothing from a sibling repo. Previously this
# walked up 1-2 levels looking for a sibling k9-aif-framework checkout
# (needed when the Containerfile copied templates from there) -- removed
# along with that cross-repo dependency (2026-09-21), so k9x_studio no
# longer cares where it's cloned relative to anything else.
AI_DIR="$PROJECT_DIR"
STUDIO_REL_PATH="."

IMAGE="k9x-studio:latest"
CONTAINER="k9x-studio"
PROJECTS_HOST_DIR="${HOME}/containers/volumes/k9x-studio/projects"

cmd="${1:-help}"

case "$cmd" in

  build)
    echo "Building $IMAGE (context: $AI_DIR, project dir: $STUDIO_REL_PATH) ..."
    cd "$AI_DIR"
    sudo podman build -t "$IMAGE" \
      --build-arg "STUDIO_DIR=$STUDIO_REL_PATH" \
      -f "$STUDIO_REL_PATH/ubuntu/Containerfile" .
    echo "Build complete: $IMAGE"
    ;;

  start)
    ENV_FILE="$PROJECT_DIR/.env"
    [[ -f "$ENV_FILE" ]] || { echo "Error: $ENV_FILE not found."; exit 1; }
    sudo mkdir -p "$PROJECTS_HOST_DIR"
    echo "Starting $CONTAINER on port 8081 ..."
    sudo podman rm -f "$CONTAINER" 2>/dev/null || true
    sudo podman run -d \
      --name "$CONTAINER" \
      --restart=always \
      -p 8081:8090 \
      -v "$PROJECTS_HOST_DIR":/k9x/projects:Z \
      -e K9X_PROJECTS_ROOT=/k9x/projects \
      --env-file "$ENV_FILE" \
      "$IMAGE"
    echo ""
    HOST_IP=$(hostname -I | awk '{print $1}')
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  k9x_studio"
    echo "  Web UI:  http://${HOST_IP}:8081/"
    echo "  Health:  http://${HOST_IP}:8081/api/health"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ;;

  stop)
    echo "Stopping $CONTAINER ..."
    sudo podman stop "$CONTAINER" 2>/dev/null || true
    echo "Stopped."
    ;;

  logs)
    sudo podman logs -f "$CONTAINER"
    ;;

  all)
    "$0" build
    "$0" start
    ;;

  help|*)
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  build   — build the Podman image ($IMAGE)"
    echo "  start   — start the container (port 8081)"
    echo "  stop    — stop the container"
    echo "  logs    — tail logs"
    echo "  all     — build + start"
    ;;

esac

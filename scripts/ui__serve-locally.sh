#!/bin/bash
# ───────────────────────────────────────────────────────────────────────────────
# Local static file server for the Playwright Service UI
#
# Serves sgraph_ai_service_playwright__api_site/ so you can open the admin
# and user UIs in a browser without deploying to S3.
#
# Pair with sp-cli__run-locally.sh to get a fully local stack:
#
#   Terminal 1:  ./scripts/sp-cli__run-locally.sh          # backend on :10071
#   Terminal 2:  ./scripts/ui__serve-locally.sh            # UI on :8090
#
# Then open http://localhost:8090 and click the ⚙ gear icon to set:
#   API URL:  http://localhost:10071
#   API Key:  (leave blank — open mode when FAST_API__AUTH__API_KEY__VALUE is unset)
#
# Usage:
#   ./scripts/ui__serve-locally.sh                         # binds 0.0.0.0:8090
#   PORT=9000 ./scripts/ui__serve-locally.sh               # custom port
# ───────────────────────────────────────────────────────────────────────────────

PORT="${PORT:-8090}"
HOST="${HOST:-0.0.0.0}"
SITE_DIR="$(cd "$(dirname "$0")/.." && pwd)/sgraph_ai_service_playwright__api_site"

if [ ! -d "$SITE_DIR" ]; then
    echo "ERROR: UI directory not found: $SITE_DIR"
    exit 1
fi

echo ""
echo "Serving UI from: $SITE_DIR"
echo ""
echo "  Landing page:  http://localhost:$PORT/"
echo "  Admin UI:      http://localhost:$PORT/admin/"
echo "  User UI:       http://localhost:$PORT/user/"
echo ""
echo "To connect to a local backend, click ⚙ in the top bar and set:"
echo "  API URL:  http://localhost:10071"
echo "  API Key:  (leave blank in open mode)"
echo ""
echo "To start the backend in another terminal:"
echo "  ./scripts/sp-cli__run-locally.sh"
echo ""

cd "$SITE_DIR" && python3 -m http.server "$PORT" --bind "$HOST"

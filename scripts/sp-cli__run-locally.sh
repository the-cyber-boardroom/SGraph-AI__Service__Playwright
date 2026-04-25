#!/bin/bash
# ───────────────────────────────────────────────────────────────────────────────
# Local dev server for the SP CLI FastAPI app (Fast_API__SP__CLI)
#
# Same surface that runs on the sp-playwright-cli Lambda:
#   /docs                          - Swagger UI
#   /openapi.json                  - raw spec
#   /ec2/playwright/{list,info,create,delete}/{name?}
#   /observability/stacks/{name?}
#
# Loads .local-server.env if present so AWS creds + API key live outside the
# repo. Without that file, /docs and /openapi.json still work; route handlers
# that talk to AWS will 500 until creds are in the environment.
#
# uvicorn factory mode targets scripts.run_sp_cli:build_app so --reload
# re-imports the app on source changes.
#
# Usage:
#   ./scripts/sp-cli__run-locally.sh                # binds 0.0.0.0:10062
#   PORT=9000 ./scripts/sp-cli__run-locally.sh      # custom port
# ───────────────────────────────────────────────────────────────────────────────

PORT="${PORT:-10062}"
HOST="${HOST:-0.0.0.0}"

# ─── Load env vars from .local-server.env (if present) ────────────────────────
if [ -f .local-server.env ]; then
    echo "Loading environment variables from .local-server.env file..."
    export $(cat .local-server.env | grep -v '^#' | grep -v '^[[:space:]]*$' | xargs)
    echo "✓ Environment variables loaded"
else
    echo "⚠️  No .local-server.env file found"
    echo "   /docs + /openapi.json will work; AWS-bound routes need AWS_*"
    echo "   creds in the environment. Optional: FAST_API__AUTH__API_KEY__VALUE"
    echo "   (unset = open mode; set = X-API-Key header required on every call)"
fi

# ─── Banner ───────────────────────────────────────────────────────────────────
echo ""
echo "Starting Fast_API__SP__CLI on http://$HOST:$PORT ..."
echo "  Swagger UI:  http://localhost:$PORT/docs"
echo "  OpenAPI:     http://localhost:$PORT/openapi.json"
echo ""

# ─── Run ──────────────────────────────────────────────────────────────────────
poetry run uvicorn scripts.run_sp_cli:build_app \
    --factory \
    --reload \
    --host "$HOST" \
    --port "$PORT" \
    --log-level info \
    --timeout-graceful-shutdown 0

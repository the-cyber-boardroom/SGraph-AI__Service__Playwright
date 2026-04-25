# ═══════════════════════════════════════════════════════════════════════════════
# scripts/run_sp_cli.py
# Local launcher for the SP CLI FastAPI app (the same one that runs on the
# sp-playwright-cli Lambda). Boots Fast_API__SP__CLI under uvicorn so /docs is
# reachable at http://localhost:8080/docs by default.
#
# Usage
# ─────
#   # Open dev mode — no API key required (matches the Lambda when the env
#   # var is unset; X-API-Key middleware short-circuits to "allow")
#   python -m scripts.run_sp_cli
#
#   # With an API key, mirroring production
#   FAST_API__AUTH__API_KEY__VALUE=local-key python -m scripts.run_sp_cli
#
#   # Custom host/port + reload-on-edit
#   python -m scripts.run_sp_cli --host 0.0.0.0 --port 9000 --reload
#
# AWS credentials
# ───────────────
# Booting the app does NOT touch AWS — Type_Safe service classes initialise
# without making network calls. The route handlers DO call AWS (EC2, AMP,
# OpenSearch, Grafana), so /ec2/playwright/* and /observability/* require
# valid AWS credentials in the environment when invoked. /docs and
# /openapi.json work without credentials.
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import sys

import uvicorn

from sgraph_ai_service_playwright__cli.fast_api.Fast_API__SP__CLI                   import Fast_API__SP__CLI


DEFAULT_HOST = '127.0.0.1'                                                          # Loopback by default; pass --host 0.0.0.0 to bind all interfaces
DEFAULT_PORT = 8080
LOG_LEVEL    = 'info'


def build_app():                                                                    # Same setup the Lambda runs through Mangum: __init__ wires API-key middleware + version, setup() registers Type_Safe exception handlers and mounts routes
    return Fast_API__SP__CLI().setup().app()


def main() -> int:
    parser = argparse.ArgumentParser(description='Run the SP CLI FastAPI app locally on uvicorn.')
    parser.add_argument('--host'  , default=DEFAULT_HOST, help=f'Bind address (default: {DEFAULT_HOST})')
    parser.add_argument('--port'  , type=int, default=DEFAULT_PORT, help=f'Bind port (default: {DEFAULT_PORT})')
    parser.add_argument('--reload', action='store_true', help='Enable uvicorn auto-reload on source change')
    args = parser.parse_args()

    print(f'\nSP CLI local launcher')
    print(f'  http://{args.host}:{args.port}/docs   (Swagger UI)')
    print(f'  http://{args.host}:{args.port}/openapi.json   (raw spec)\n')

    if args.reload:                                                                 # Reload mode needs a factory string so uvicorn can re-import on file changes
        uvicorn.run('scripts.run_sp_cli:build_app', factory=True,
                    host=args.host, port=args.port, log_level=LOG_LEVEL, reload=True)
    else:
        uvicorn.run(build_app(), host=args.host, port=args.port, log_level=LOG_LEVEL)
    return 0


if __name__ == '__main__':
    sys.exit(main())

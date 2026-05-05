# ═══════════════════════════════════════════════════════════════════════════════
# scripts/run_sp_cli.py
# Local launcher for the SG Compute control plane (Fast_API__Compute).
# Serves /api/* (modern) and /legacy/* (deprecated SP CLI surface) from one
# process. Reachable at http://localhost:8080/docs by default.
#
# Usage
# ─────
#   # Open dev mode — no API key required
#   python -m scripts.run_sp_cli
#
#   # Custom host/port + reload-on-edit
#   python -m scripts.run_sp_cli --host 0.0.0.0 --port 9000 --reload
#
# AWS credentials
# ───────────────
# Booting the app does NOT touch AWS. Route handlers for /legacy/ec2/* and
# /legacy/observability/* require valid credentials when invoked. /docs and
# /openapi.json work without credentials.
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import sys

import uvicorn

from sg_compute.control_plane.Fast_API__Compute                                    import Fast_API__Compute


DEFAULT_HOST = '127.0.0.1'                                                          # Loopback by default; pass --host 0.0.0.0 to bind all interfaces
DEFAULT_PORT = 8080
LOG_LEVEL    = 'info'


def build_app():
    return Fast_API__Compute().setup().app()


def main() -> int:
    parser = argparse.ArgumentParser(description='Run the SG Compute FastAPI app locally on uvicorn.')
    parser.add_argument('--host'  , default=DEFAULT_HOST, help=f'Bind address (default: {DEFAULT_HOST})')
    parser.add_argument('--port'  , type=int, default=DEFAULT_PORT, help=f'Bind port (default: {DEFAULT_PORT})')
    parser.add_argument('--reload', action='store_true', help='Enable uvicorn auto-reload on source change')
    args = parser.parse_args()

    print(f'\nSG Compute local launcher')
    print(f'  http://{args.host}:{args.port}/docs      (Swagger UI)')
    print(f'  http://{args.host}:{args.port}/api/specs (spec catalogue)')
    print(f'  http://{args.host}:{args.port}/legacy/   (deprecated SP CLI surface)\n')

    if args.reload:                                                                 # Reload mode needs a factory string so uvicorn can re-import on file changes
        uvicorn.run('scripts.run_sp_cli:build_app', factory=True,
                    host=args.host, port=args.port, log_level=LOG_LEVEL, reload=True)
    else:
        uvicorn.run(build_app(), host=args.host, port=args.port, log_level=LOG_LEVEL)
    return 0


if __name__ == '__main__':
    sys.exit(main())

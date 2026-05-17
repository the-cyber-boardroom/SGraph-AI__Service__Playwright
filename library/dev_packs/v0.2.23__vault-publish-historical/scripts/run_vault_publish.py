# ═══════════════════════════════════════════════════════════════════════════════
# scripts/run_vault_publish.py
# Local launcher for the vault-publish FastAPI app (Fast_API__Vault_Publish).
# One Publish__Service is shared across requests, so state persists for the life
# of the process — register a slug, then status / wake / list / unpublish it.
#
# Usage
# ─────
#   # Open dev mode — no API key required
#   python -m scripts.run_vault_publish
#
#   # Custom host/port + reload-on-edit
#   python -m scripts.run_vault_publish --host 0.0.0.0 --port 9000 --reload
#
# Then open http://127.0.0.1:8090/docs for the Swagger UI, or curl the routes
# under /vault-publish/*. A demo slug 'hello-world' is seeded end to end so
# wake() works out of the box (the manifest-publish step is on the SG/Send side
# and has no endpoint here).
#
# AWS credentials
# ───────────────
# Booting the app does NOT touch AWS — the SG/Send and AWS boundaries are wired
# with in-memory stand-ins. No credentials are required.
# ═══════════════════════════════════════════════════════════════════════════════

import argparse

import uvicorn

from vault_publish.fast_api.Fast_API__Vault_Publish                              import Fast_API__Vault_Publish

DEFAULT_HOST = '127.0.0.1'                                                          # loopback by default; pass --host 0.0.0.0 to bind all interfaces
DEFAULT_PORT = 8090
LOG_LEVEL    = 'info'


def build_app():
    return Fast_API__Vault_Publish().setup().app()


def main() -> int:
    parser = argparse.ArgumentParser(description='Run the vault-publish FastAPI app locally on uvicorn.')
    parser.add_argument('--host'  , default=DEFAULT_HOST, help=f'Bind address (default: {DEFAULT_HOST})')
    parser.add_argument('--port'  , type=int, default=DEFAULT_PORT, help=f'Bind port (default: {DEFAULT_PORT})')
    parser.add_argument('--reload', action='store_true', help='Enable uvicorn auto-reload on source change')
    args = parser.parse_args()

    print(f'\nvault-publish local launcher')
    print(f'  http://{args.host}:{args.port}/docs                  (Swagger UI)')
    print(f'  http://{args.host}:{args.port}/vault-publish/list     (registered slugs — seeded: hello-world)')
    print(f'  http://{args.host}:{args.port}/vault-publish/health   (infrastructure layers)\n')

    if args.reload:
        uvicorn.run('scripts.run_vault_publish:build_app', host=args.host, port=args.port,
                    log_level=LOG_LEVEL, factory=True, reload=True)
    else:
        uvicorn.run(build_app(), host=args.host, port=args.port, log_level=LOG_LEVEL)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

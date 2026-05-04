# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — uvicorn ASGI entrypoint
#
# supervisord.conf starts uvicorn with `sg_compute_specs.mitmproxy.api.app:app`.
# Importing this module builds the FastAPI instance as a side effect.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.mitmproxy.api.Fast_API__Agent_Mitmproxy                        import Fast_API__Agent_Mitmproxy


app = Fast_API__Agent_Mitmproxy().setup().app()

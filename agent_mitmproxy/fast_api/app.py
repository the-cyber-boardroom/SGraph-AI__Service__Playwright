# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — uvicorn ASGI entrypoint
#
# supervisord.conf starts uvicorn with `agent_mitmproxy.fast_api.app:app`.
# Importing this module builds the FastAPI instance as a side effect.
# ═══════════════════════════════════════════════════════════════════════════════

from agent_mitmproxy.fast_api.Fast_API__Agent_Mitmproxy                                  import Fast_API__Agent_Mitmproxy


app = Fast_API__Agent_Mitmproxy().setup().app()

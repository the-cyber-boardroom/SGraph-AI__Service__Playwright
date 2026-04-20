#!/bin/sh
# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — container entrypoint
#
# 1. Seed /app/current_interceptor.py from the baked default (gives the
#    admin /config/interceptor endpoint something to return before any upload).
# 2. Exec supervisord — it launches mitmweb + uvicorn as siblings and
#    forwards SIGTERM on shutdown.
# ═══════════════════════════════════════════════════════════════════════════════

set -eu

if [ ! -f /app/current_interceptor.py ]; then
    cp /app/agent_mitmproxy/addons/default_interceptor.py /app/current_interceptor.py
fi

exec supervisord -c /app/supervisord.conf

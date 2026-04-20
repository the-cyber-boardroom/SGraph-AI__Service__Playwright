# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Addon registry
#
# mitmweb is launched with `-s <this file>` so it picks up every registered
# addon via the module-level `addons = [...]` list.
# ═══════════════════════════════════════════════════════════════════════════════

from agent_mitmproxy.addons.default_interceptor                                      import addons as interceptor_addons
from agent_mitmproxy.addons.audit_log_addon                                          import addons as audit_addons


addons = [*interceptor_addons, *audit_addons]

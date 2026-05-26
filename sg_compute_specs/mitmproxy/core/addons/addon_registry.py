# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Addon registry
#
# mitmweb is launched with `-s <this file>` so it picks up every registered
# addon via the module-level `addons = [...]` list.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.mitmproxy.core.addons.default_interceptor          import addons as interceptor_addons
from sg_compute_specs.mitmproxy.core.addons.audit_log_addon              import addons as audit_addons
from sg_compute_specs.mitmproxy.core.addons.prometheus_metrics_addon     import addons as metrics_addons
from sg_compute_specs.mitmproxy.core.addons.run_capture_addon            import addons as run_capture_addons


addons = [*interceptor_addons, *audit_addons, *metrics_addons, *run_capture_addons]

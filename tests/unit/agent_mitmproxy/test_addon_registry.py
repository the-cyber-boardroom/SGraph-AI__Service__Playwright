# ═══════════════════════════════════════════════════════════════════════════════
# Tests — agent_mitmproxy/addons/addon_registry.py
#
# mitmweb -s <this file> loads the module-level `addons` list. The registry
# must expose both the interceptor and the audit log addon, in that order.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                        import TestCase

from agent_mitmproxy.addons.addon_registry                                           import addons
from agent_mitmproxy.addons.audit_log_addon                                          import Audit_Log
from agent_mitmproxy.addons.default_interceptor                                      import Default_Interceptor
from agent_mitmproxy.addons.prometheus_metrics_addon                                 import Prometheus_Metrics


class test_addon_registry(TestCase):

    def test__exposes_both_addons_in_order(self):
        assert len(addons)                  == 3
        assert isinstance(addons[0], Default_Interceptor )
        assert isinstance(addons[1], Audit_Log           )
        assert isinstance(addons[2], Prometheus_Metrics  )

# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute_specs.mitmproxy.core.addons.addon_registry
#
# mitmweb -s <this file> loads the module-level `addons` list. The registry
# must expose both the interceptor and the audit log addon, in that order.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                        import TestCase

from sg_compute_specs.mitmproxy.core.addons.addon_registry                           import addons
from sg_compute_specs.mitmproxy.core.addons.audit_log_addon                          import Audit_Log
from sg_compute_specs.mitmproxy.core.addons.default_interceptor                      import Default_Interceptor
from sg_compute_specs.mitmproxy.core.addons.prometheus_metrics_addon                 import Prometheus_Metrics


class test_addon_registry(TestCase):

    def test__exposes_both_addons_in_order(self):
        assert len(addons)                  == 3
        assert isinstance(addons[0], Default_Interceptor )
        assert isinstance(addons[1], Audit_Log           )
        assert isinstance(addons[2], Prometheus_Metrics  )

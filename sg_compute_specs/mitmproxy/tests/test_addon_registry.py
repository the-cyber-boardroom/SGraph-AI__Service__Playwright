# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute_specs.mitmproxy.core.addons.addon_registry
#
# mitmweb -s <this file> loads the module-level `addons` list. The registry must
# expose the interceptor, audit-log, metrics, and per-run capture addons, in order.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                        import TestCase

from sg_compute_specs.mitmproxy.core.addons.addon_registry                           import addons
from sg_compute_specs.mitmproxy.core.addons.audit_log_addon                          import Audit_Log
from sg_compute_specs.mitmproxy.core.addons.default_interceptor                      import Default_Interceptor
from sg_compute_specs.mitmproxy.core.addons.prometheus_metrics_addon                 import Prometheus_Metrics
from sg_compute_specs.mitmproxy.core.addons.run_capture_addon                        import Run_Capture


class test_addon_registry(TestCase):

    def test__exposes_all_addons_in_order(self):
        assert len(addons)                  == 4
        assert isinstance(addons[0], Default_Interceptor )
        assert isinstance(addons[1], Audit_Log           )
        assert isinstance(addons[2], Prometheus_Metrics  )
        assert isinstance(addons[3], Run_Capture         )

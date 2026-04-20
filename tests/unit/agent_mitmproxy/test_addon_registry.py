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


class test_addon_registry(TestCase):

    def test__exposes_both_addons_in_order(self):
        assert len(addons)                  == 2
        assert isinstance(addons[0], Default_Interceptor)
        assert isinstance(addons[1], Audit_Log         )

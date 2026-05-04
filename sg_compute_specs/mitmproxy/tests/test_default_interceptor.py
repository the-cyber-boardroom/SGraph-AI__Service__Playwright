# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute_specs.mitmproxy.core.addons.default_interceptor
#
# Duck-typed against a fake Flow (SimpleNamespace) — mitmproxy does not need to
# be installed for these tests to run. The addon only touches attributes that
# mitmproxy populates at runtime: flow.request.headers, flow.response.headers,
# flow.metadata.
# ═══════════════════════════════════════════════════════════════════════════════

import time
from types                                                                           import SimpleNamespace
from unittest                                                                        import TestCase

from sg_compute_specs.mitmproxy.core.addons.default_interceptor                      import (Default_Interceptor      ,
                                                                                             HEADER__ELAPSED_MS        ,
                                                                                             HEADER__REQUEST_ID        ,
                                                                                             HEADER__REQUEST_TS        ,
                                                                                             HEADER__VERSION           ,
                                                                                             METADATA__REQUEST_ID      ,
                                                                                             addons                    )


def _make_flow(timestamp_start: float = None) -> SimpleNamespace:
    return SimpleNamespace(metadata = {},
                           request  = SimpleNamespace(headers={}, timestamp_start=timestamp_start),
                           response = SimpleNamespace(headers={}))


class test_Default_Interceptor(TestCase):

    def test__request_stamps_id_and_timestamp(self):
        addon = Default_Interceptor()
        flow  = _make_flow()

        addon.request(flow)

        assert flow.metadata[METADATA__REQUEST_ID]        == flow.request.headers[HEADER__REQUEST_ID]
        assert len(flow.request.headers[HEADER__REQUEST_ID]) == 12                           # secrets.token_hex(6) → 12 chars
        assert flow.request.headers[HEADER__REQUEST_TS].endswith('+00:00')                    # UTC isoformat

    def test__response_echoes_id_and_version(self):
        addon = Default_Interceptor()
        flow  = _make_flow(timestamp_start=time.time() - 0.050)                              # simulate 50ms-old request

        addon.request (flow)
        addon.response(flow)

        request_id = flow.metadata[METADATA__REQUEST_ID]
        assert flow.response.headers[HEADER__REQUEST_ID] == request_id
        assert flow.response.headers[HEADER__VERSION  ].startswith('v0.1.')
        assert int(flow.response.headers[HEADER__ELAPSED_MS]) >= 40                          # ≥40ms — allow slack for CI jitter

    def test__response_without_timestamp_start_omits_elapsed(self):                         # Defensive — metadata-only test flow must not crash
        addon = Default_Interceptor()
        flow  = _make_flow(timestamp_start=None)

        addon.request (flow)
        addon.response(flow)

        assert HEADER__ELAPSED_MS not in flow.response.headers                               # No timestamp → no elapsed header

    def test__addons_export(self):
        assert len(addons) == 1
        assert isinstance(addons[0], Default_Interceptor)

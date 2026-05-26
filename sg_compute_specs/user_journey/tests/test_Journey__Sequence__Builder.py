# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Journey__Sequence__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.mitmproxy.core.addons.run_capture_addon                        import HEADER__RUN_ID as ADDON__HEADER__RUN_ID
from sg_compute_specs.user_journey.core.schemas.journey.Schema__Journey__Definition  import Schema__Journey__Definition
from sg_compute_specs.user_journey.core.worker.Journey__Sequence__Builder            import Journey__Sequence__Builder, HEADER__RUN_ID


class TestJourneySequenceBuilder:

    def _journey(self):
        journey = Schema__Journey__Definition(target_url='https://shop.test/', environment='dev')
        journey.steps.append({'action': 'navigate', 'url': 'https://shop.test/'})
        journey.steps.append({'action': 'get_url'})
        return journey

    def test__copies_steps(self):
        request = Journey__Sequence__Builder().build(self._journey(), 'run-7')
        assert len(request.steps)        == 2
        assert request.steps[0]['action'] == 'navigate'
        assert request.steps[1]['action'] == 'get_url'

    def test__injects_run_id_header(self):
        request = Journey__Sequence__Builder().build(self._journey(), 'run-7')
        headers = {str(k): str(v) for k, v in request.credentials.extra_http_headers.items()}
        assert headers.get('x-sg-run-id') == 'run-7'                                # header name lowercased; value preserved

    def test__has_default_capture_and_sequence_config(self):
        request = Journey__Sequence__Builder().build(self._journey(), 'run-7')
        assert request.capture_config  is not None                                  # auto-defaulted by Schema__Sequence__Request
        assert request.sequence_config is not None

    def test__header_name_matches_mitmproxy_addon(self):                            # the two must never drift
        assert HEADER__RUN_ID == ADDON__HEADER__RUN_ID == 'X-SG-Run-Id'

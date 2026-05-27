# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Journey__Local__Runner (pure parts: load_journey + new_run_id)
# run() is the gated integration (real Chromium + mitmproxy), exercised by the
# `sg user-journey run-local` verb, not here.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from sg_compute_specs.user_journey.core.worker.Journey__Local__Runner import Journey__Local__Runner


def _journey_file(tmp_path):
    path = tmp_path / 'checkout.json'
    path.write_text(json.dumps({'journey_id' : 'checkout',
                                'target_url' : 'https://shop.test/',
                                'environment': 'prod',
                                'steps'      : [{'action': 'goto', 'url': 'https://shop.test/'}],
                                'assertions' : [],
                                'tags'       : []}), encoding='utf-8')
    return str(path)


class TestJourneyLocalRunner:

    def test__load_journey(self, tmp_path):
        journey = Journey__Local__Runner().load_journey(_journey_file(tmp_path))
        assert str(journey.journey_id) == 'checkout'
        assert str(journey.target_url) == 'https://shop.test/'
        assert list(journey.steps)     == [{'action': 'goto', 'url': 'https://shop.test/'}]

    def test__new_run_id_is_prefixed_and_unique(self):
        runner = Journey__Local__Runner()
        first  = runner.new_run_id()
        second = runner.new_run_id()
        assert first.startswith('local-')
        assert first != second

    def test__capture_client_honours_config(self):
        runner                 = Journey__Local__Runner()
        runner.capture_url     = 'http://127.0.0.1:8000'
        runner.capture_api_key = 'k'
        client = runner.capture_client()
        assert str(client.base_url) == 'http://127.0.0.1:8000'
        assert str(client.api_key)  == 'k'

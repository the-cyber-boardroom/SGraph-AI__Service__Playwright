# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Sequence Schemas (spec §5.8)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Config           import Schema__Sequence__Config
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Request          import Schema__Sequence__Request
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Response         import Schema__Sequence__Response


class test_Schema__Sequence__Config(TestCase):

    def test__defaults(self):
        cfg = Schema__Sequence__Config()
        assert cfg.halt_on_error           is True
        assert cfg.default_step_timeout_ms == 30_000
        assert cfg.total_timeout_ms        == 300_000


class test_Schema__Sequence__Request(TestCase):

    def test__defaults(self):                                                      # v0.1.24 — stateless request; no session_id / close_session_after
        req = Schema__Sequence__Request()
        assert req.steps          == []
        assert req.browser_config is None
        assert req.credentials    is None
        assert req.trace_id       is None


class test_Schema__Sequence__Response(TestCase):

    def test__defaults(self):
        resp = Schema__Sequence__Response()
        assert resp.steps_total   == 0
        assert resp.steps_passed  == 0
        assert resp.steps_failed  == 0
        assert resp.steps_skipped == 0
        assert resp.step_results  == []
        assert resp.artefacts     == []

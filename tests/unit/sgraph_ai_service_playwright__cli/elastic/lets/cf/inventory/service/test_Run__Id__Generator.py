# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Run__Id__Generator
# Pins the run-id format and the seam contract: tests subclass and override
# now_iso() / short_sha() to drive deterministic ids, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Run__Id__Generator import Run__Id__Generator


class Deterministic__Run__Id__Generator(Run__Id__Generator):                        # Subclass-and-override; no mocks per CLAUDE.md
    fixture_iso  : str = '20260425T103042Z'
    fixture_sha  : str = 'a3f2'

    def now_iso(self) -> str:
        return self.fixture_iso

    def short_sha(self) -> str:
        return self.fixture_sha


class test_Run__Id__Generator(TestCase):

    def test_format_with_overridden_seams(self):                                    # Pins the wire format end to end
        gen = Deterministic__Run__Id__Generator()
        assert gen.generate(source='cf-realtime', verb='load') == '20260425T103042Z-cf-realtime-load-a3f2'

    def test_output_passes_safe_str_validation(self):                               # The id must be valid input for Safe_Str__Pipeline__Run__Id
        gen      = Deterministic__Run__Id__Generator()
        run_id   = gen.generate(source='cf-realtime', verb='load')
        wrapped  = Safe_Str__Pipeline__Run__Id(run_id)
        assert wrapped == run_id

    def test_real_now_iso_matches_compact_format(self):                             # The default now_iso() returns 16-char compact ISO ("YYYYMMDDTHHMMSSZ")
        s = Run__Id__Generator().now_iso()
        assert len(s) == 16
        assert s.endswith('Z')
        assert 'T' in s

    def test_real_short_sha_is_4_hex(self):                                         # token_hex(2) returns 4 hex chars
        s = Run__Id__Generator().short_sha()
        assert len(s) == 4
        assert all(c in '0123456789abcdef' for c in s)

    def test_two_calls_yield_different_ids(self):                                   # Real generator should virtually always produce unique ids — short_sha gives 65k space
        gen = Run__Id__Generator()
        ids = {gen.generate(source='cf-realtime', verb='load') for _ in range(50)}
        assert len(ids) >= 49                                                       # Allow one statistical collision in 50 attempts; in practice always 50

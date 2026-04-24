# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Synthetic__Data__Generator
# ═══════════════════════════════════════════════════════════════════════════════

from datetime                                                                       import datetime, timedelta, timezone
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Log__Document   import List__Schema__Log__Document
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Log__Level               import Enum__Log__Level
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Log__Document        import Schema__Log__Document
from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator


class test_Synthetic__Data__Generator(TestCase):

    def test_generate__count_matches(self):
        gen  = Synthetic__Data__Generator(seed=42, window_days=7)
        docs = gen.generate(50)
        assert type(docs) is List__Schema__Log__Document
        assert len(docs)  == 50
        for d in docs:
            assert type(d)       is Schema__Log__Document
            assert type(d.level) is Enum__Log__Level
            assert str(d.timestamp).endswith('Z')                                   # UTC ISO-8601 with millisecond precision

    def test_generate__deterministic_pool_choices_with_seed(self):                  # Same seed → same level/service/message picks; timestamps anchored to now() will drift between runs
        a = Synthetic__Data__Generator(seed=123).generate(20)
        b = Synthetic__Data__Generator(seed=123).generate(20)
        assert [str(d.level  ) for d in a] == [str(d.level  ) for d in b]
        assert [str(d.service) for d in a] == [str(d.service) for d in b]
        assert [str(d.message) for d in a] == [str(d.message) for d in b]
        assert [d.duration_ms  for d in a] == [d.duration_ms  for d in b]

    def test_generate__timestamps_within_window(self):
        window = 3
        gen    = Synthetic__Data__Generator(seed=7, window_days=window)
        before = datetime.now(tz=timezone.utc) - timedelta(days=window, seconds=5)  # 5s slack for clock drift between gen and assert
        docs   = gen.generate(100)
        after  = datetime.now(tz=timezone.utc) + timedelta(seconds=5)
        for d in docs:
            ts = datetime.strptime(str(d.timestamp), '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
            assert before <= ts <= after

    def test_generate__zero_count_returns_empty(self):
        docs = Synthetic__Data__Generator(seed=1).generate(0)
        assert len(docs) == 0

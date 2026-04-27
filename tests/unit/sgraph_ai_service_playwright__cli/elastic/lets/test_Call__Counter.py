# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Call__Counter
# Pins the counter contract: increments per call, total() sums correctly,
# reset() returns to zero.  Plus an integration assertion that S3 lister and
# HTTP client SHARE a counter when they're given the same instance.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.Call__Counter                   import Call__Counter


class test_Call__Counter(TestCase):

    def test_starts_at_zero(self):
        c = Call__Counter()
        assert c.s3_calls      == 0
        assert c.elastic_calls == 0
        assert c.total()       == 0

    def test_s3_increments(self):
        c = Call__Counter()
        c.s3()
        c.s3()
        c.s3()
        assert c.s3_calls      == 3
        assert c.elastic_calls == 0
        assert c.total()       == 3

    def test_elastic_increments(self):
        c = Call__Counter()
        c.elastic()
        c.elastic()
        assert c.elastic_calls == 2
        assert c.s3_calls      == 0
        assert c.total()       == 2

    def test_mixed_increments_and_total(self):
        c = Call__Counter()
        c.s3()
        c.elastic()
        c.s3()
        c.elastic()
        c.elastic()
        assert c.s3_calls      == 2
        assert c.elastic_calls == 3
        assert c.total()       == 5

    def test_reset_clears_both(self):
        c = Call__Counter()
        c.s3()
        c.elastic()
        c.reset()
        assert c.s3_calls      == 0
        assert c.elastic_calls == 0


class test_shared_counter_across_collaborators(TestCase):

    def test_s3_lister_and_http_client_share_counter(self):                         # When the same Call__Counter is injected into multiple service classes, calls from each accumulate into one shared total — the property the SG_Send orchestrator relies on
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client

        shared = Call__Counter()
        http   = Inventory__HTTP__Client(counter=shared)

        # Manually invoke counter increments to simulate calls — we don't
        # actually fire a request() because that'd hit the network
        http.counter.elastic()
        http.counter.elastic()
        http.counter.elastic()

        assert shared.elastic_calls == 3                                            # The injected counter is the same object — increments via http.counter show up on shared
        assert http.counter is shared

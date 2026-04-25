# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Inventory__Load__Request
# Pins the request shape and the empty-default semantics (service auto-resolves
# bucket / prefix / run_id / stack_name when those are empty).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Load__Request import Schema__Inventory__Load__Request


class test_Schema__Inventory__Load__Request(TestCase):

    def test_default_construction_is_all_empty_or_zero(self):                       # Every field has a sensible default — caller can pass nothing
        req = Schema__Inventory__Load__Request()
        assert req.bucket     == ''
        assert req.prefix     == ''
        assert req.all        is False
        assert req.max_keys   == 0
        assert req.run_id     == ''
        assert req.stack_name == ''
        assert req.dry_run    is False

    def test_with_explicit_prefix(self):                                            # Most common CLI invocation: a date prefix
        req = Schema__Inventory__Load__Request(prefix='cloudfront-realtime/2026/04/25/')
        assert req.prefix == 'cloudfront-realtime/2026/04/25/'

    def test_dry_run_flag(self):
        req = Schema__Inventory__Load__Request(dry_run=True)
        assert req.dry_run is True

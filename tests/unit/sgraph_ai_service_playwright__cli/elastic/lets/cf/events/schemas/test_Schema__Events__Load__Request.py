# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Events__Load__Request
# Defaults are all empty/zero/false — service auto-resolves on persist.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Load__Request import Schema__Events__Load__Request


class test_Schema__Events__Load__Request(TestCase):

    def test_default_construction(self):
        req = Schema__Events__Load__Request()
        assert req.bucket          == ''
        assert req.prefix          == ''
        assert req.all             is False
        assert req.max_files       == 0
        assert req.from_inventory  is False
        assert req.run_id          == ''
        assert req.dry_run         is False

    def test_from_inventory_flag(self):
        req = Schema__Events__Load__Request(from_inventory=True, max_files=50)
        assert req.from_inventory is True
        assert req.max_files       == 50

    def test_dry_run_flag(self):
        req = Schema__Events__Load__Request(dry_run=True)
        assert req.dry_run is True

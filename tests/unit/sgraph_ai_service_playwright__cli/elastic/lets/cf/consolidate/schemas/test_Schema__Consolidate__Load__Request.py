# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__Consolidate__Load__Request
# Pins defaults and confirms from_inventory=True is the safe default.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Consolidate__Load__Request import Schema__Consolidate__Load__Request, DEFAULT_COMPAT_REGION


class test_Schema__Consolidate__Load__Request(TestCase):

    def test_default_construction(self):
        req = Schema__Consolidate__Load__Request()
        assert str(req.bucket)        == ''
        assert str(req.date_iso)      == ''
        assert str(req.compat_region) == DEFAULT_COMPAT_REGION
        assert req.from_inventory     is True
        assert req.max_files          == 0
        assert req.dry_run            is False
        assert str(req.run_id)        == ''

    def test_with_values(self):
        req = Schema__Consolidate__Load__Request(
            bucket         = '745506449035--sgraph-send-cf-logs--eu-west-2',
            date_iso       = '2026-04-27'                                   ,
            from_inventory = True                                            ,
            max_files      = 50                                              ,
            dry_run        = True                                            ,
        )
        assert str(req.bucket)    == '745506449035--sgraph-send-cf-logs--eu-west-2'
        assert str(req.date_iso)  == '2026-04-27'
        assert req.max_files      == 50
        assert req.dry_run        is True

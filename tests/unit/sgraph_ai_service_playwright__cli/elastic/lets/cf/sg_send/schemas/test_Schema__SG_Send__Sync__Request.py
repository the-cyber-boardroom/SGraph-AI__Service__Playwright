# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Schema__SG_Send__Sync__Request
# Pins defaults, field types, and the Type_Safe zero-value contract.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.schemas.Schema__SG_Send__Sync__Request import Schema__SG_Send__Sync__Request


class test_Schema__SG_Send__Sync__Request(TestCase):

    def test_defaults(self):
        req = Schema__SG_Send__Sync__Request()
        assert str(req.sync_date)  == ''                                            # Empty → today UTC resolved at runtime
        assert req.max_files       == 0                                             # 0 = unlimited
        assert req.dry_run         is False
        assert str(req.bucket)     == ''                                            # Empty → SG_SEND__DEFAULT_BUCKET
        assert str(req.region)     == ''                                            # Empty → boto3 falls through to AWS_DEFAULT_REGION
        assert str(req.stack_name) == ''                                            # Empty → auto-pick

    def test_explicit_date_accepted(self):
        from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text import Safe_Str__Text
        req = Schema__SG_Send__Sync__Request(sync_date=Safe_Str__Text('2026-04-27'))
        assert str(req.sync_date) == '2026-04-27'

    def test_max_files_set(self):
        req = Schema__SG_Send__Sync__Request(max_files=50)
        assert req.max_files == 50

    def test_dry_run_toggle(self):
        req = Schema__SG_Send__Sync__Request(dry_run=True)
        assert req.dry_run is True

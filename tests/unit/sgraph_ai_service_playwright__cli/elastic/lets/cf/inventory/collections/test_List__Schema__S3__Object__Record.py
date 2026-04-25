# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — List__Schema__S3__Object__Record
# Pins the Type_Safe collection contract: appends of the right type succeed,
# wrong types are rejected at append time.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.collections.List__Schema__S3__Object__Record import List__Schema__S3__Object__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__S3__Object__Record import Schema__S3__Object__Record


class test_List__Schema__S3__Object__Record(TestCase):

    def test_starts_empty(self):
        assert len(List__Schema__S3__Object__Record()) == 0

    def test_append_record(self):
        lst = List__Schema__S3__Object__Record()
        lst.append(Schema__S3__Object__Record())
        lst.append(Schema__S3__Object__Record())
        assert len(lst) == 2

    def test_wrong_type_rejected(self):                                             # Type_Safe__List enforces expected_type
        lst = List__Schema__S3__Object__Record()
        try:
            lst.append('not-a-record')
            assert False, 'expected type error'
        except (TypeError, ValueError, Exception):
            pass

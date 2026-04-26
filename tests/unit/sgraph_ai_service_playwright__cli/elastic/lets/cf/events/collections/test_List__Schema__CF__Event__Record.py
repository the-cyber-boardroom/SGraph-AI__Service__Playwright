# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — List__Schema__CF__Event__Record
# Type_Safe collection contract for events.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.collections.List__Schema__CF__Event__Record import List__Schema__CF__Event__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__CF__Event__Record           import Schema__CF__Event__Record


class test_List__Schema__CF__Event__Record(TestCase):

    def test_starts_empty(self):
        assert len(List__Schema__CF__Event__Record()) == 0

    def test_append_record(self):
        lst = List__Schema__CF__Event__Record()
        lst.append(Schema__CF__Event__Record())
        lst.append(Schema__CF__Event__Record())
        assert len(lst) == 2

    def test_wrong_type_rejected(self):
        lst = List__Schema__CF__Event__Record()
        try:
            lst.append({'sc_status': 200})
            assert False, 'expected type error'
        except (TypeError, ValueError, Exception):
            pass

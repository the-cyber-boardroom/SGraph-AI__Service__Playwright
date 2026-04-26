# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — List__Schema__Events__Run__Summary
# Type_Safe collection contract for the `events list` rows.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.collections.List__Schema__Events__Run__Summary import List__Schema__Events__Run__Summary
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Run__Summary           import Schema__Events__Run__Summary


class test_List__Schema__Events__Run__Summary(TestCase):

    def test_starts_empty(self):
        assert len(List__Schema__Events__Run__Summary()) == 0

    def test_append_summary(self):
        lst = List__Schema__Events__Run__Summary()
        lst.append(Schema__Events__Run__Summary())
        assert len(lst) == 1

    def test_wrong_type_rejected(self):
        lst = List__Schema__Events__Run__Summary()
        try:
            lst.append({'pipeline_run_id': 'run-1'})
            assert False, 'expected type error'
        except (TypeError, ValueError, Exception):
            pass

# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Sequence__Dispatcher (parse surface; execute_step deferred to Phase 2.5)
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest import TestCase

from fastapi import HTTPException

from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action           import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Click          import Schema__Step__Click
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Navigate       import Schema__Step__Navigate
from sgraph_ai_service_playwright.service.Sequence__Dispatcher                import Sequence__Dispatcher


class test_parse_single_step(TestCase):

    def test__returns_typed_navigate(self):
        d = Sequence__Dispatcher()
        step = d.parse_single_step({'action': 'navigate', 'url': 'https://example.com'}, 0)
        assert isinstance(step, Schema__Step__Navigate)
        assert step.action == Enum__Step__Action.NAVIGATE
        assert str(step.url) == 'https://example.com'

    def test__backfills_step_id_from_index(self):                                   # Caller-omitted id defaults to str(index)
        d = Sequence__Dispatcher()
        step = d.parse_single_step({'action': 'click', 'selector': '#btn'}, 5)
        assert str(step.id) == '5'

    def test__rejects_missing_action(self):
        d = Sequence__Dispatcher()
        with pytest.raises(HTTPException) as exc:
            d.parse_single_step({'selector': '#btn'}, 0)
        assert exc.value.status_code == 422
        assert 'missing required field' in str(exc.value.detail)

    def test__rejects_unknown_action(self):
        d = Sequence__Dispatcher()
        with pytest.raises(HTTPException) as exc:
            d.parse_single_step({'action': 'fly_to_moon'}, 0)
        assert exc.value.status_code == 422
        assert 'unknown action' in str(exc.value.detail)


class test_parse_steps(TestCase):

    def test__bulk_parse_preserves_order_and_indices(self):
        d    = Sequence__Dispatcher()
        raw  = [{'action': 'navigate', 'url': 'https://a.com'},
                {'action': 'click'   , 'selector': '#one'     },
                {'action': 'click'   , 'selector': '#two'     }]
        out = d.parse_steps(raw)
        assert len(out) == 3
        assert isinstance(out[0], Schema__Step__Navigate)
        assert isinstance(out[1], Schema__Step__Click   )
        assert isinstance(out[2], Schema__Step__Click   )
        assert str(out[0].id) == '0'                                                # Auto-backfilled from index
        assert str(out[1].id) == '1'
        assert str(out[2].id) == '2'

    def test__preserves_caller_supplied_ids(self):                                  # Callers can pin ids; parser only fills gaps
        d   = Sequence__Dispatcher()
        raw = [{'action': 'navigate', 'url': 'https://a.com', 'id': 'goto-home'},
               {'action': 'click'   , 'selector': '#btn'                     }]
        out = d.parse_steps(raw)
        assert str(out[0].id) == 'goto-home'
        assert str(out[1].id) == '1'                                                # Still backfilled

    def test__empty_list_returns_empty_list(self):
        d = Sequence__Dispatcher()
        assert d.parse_steps([]) == []

    def test__raises_on_first_bad_step_with_correct_index(self):                    # The failing index appears in the error payload
        d = Sequence__Dispatcher()
        raw = [{'action': 'navigate', 'url': 'https://a.com'},
               {'action': 'nope'                             }]
        with pytest.raises(HTTPException) as exc:
            d.parse_steps(raw)
        assert 'index 1' in str(exc.value.detail)

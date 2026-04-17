# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Step Schema Registry + Parsing Helpers (spec §8)
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest import TestCase

from fastapi import HTTPException

from sgraph_ai_service_playwright.dispatcher.step_schema_registry          import (STEP_SCHEMAS,
                                                                                   STEP_RESULT_SCHEMAS,
                                                                                   parse_step,
                                                                                   result_schema_for)
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action         import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base import Schema__Step__Result__Base
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Get_Content import Schema__Step__Result__Get_Content
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Get_Url import Schema__Step__Result__Get_Url
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Evaluate import Schema__Step__Result__Evaluate
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Click        import Schema__Step__Click
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Navigate     import Schema__Step__Navigate


class test_STEP_SCHEMAS(TestCase):

    def test__covers_every_action(self):                                            # Registry must map every Enum__Step__Action variant
        expected = set(Enum__Step__Action)
        actual   = set(STEP_SCHEMAS.keys())
        assert actual == expected

    def test__maps_navigate_to_navigate_schema(self):
        assert STEP_SCHEMAS[Enum__Step__Action.NAVIGATE] is Schema__Step__Navigate


class test_STEP_RESULT_SCHEMAS(TestCase):

    def test__contains_only_typed_result_actions(self):                             # Actions not listed fall back to base
        assert set(STEP_RESULT_SCHEMAS.keys()) == {
            Enum__Step__Action.GET_CONTENT,
            Enum__Step__Action.GET_URL,
            Enum__Step__Action.EVALUATE,
        }


class test_parse_step(TestCase):

    def test__parses_navigate(self):
        step = parse_step({'action': 'navigate', 'url': 'https://example.com'}, 0)
        assert isinstance(step, Schema__Step__Navigate)
        assert str(step.url) == 'https://example.com'

    def test__parses_click(self):
        step = parse_step({'action': 'click', 'selector': '#submit'}, 3)
        assert isinstance(step, Schema__Step__Click)

    def test__defaults_missing_id_to_index(self):
        step = parse_step({'action': 'get_url'}, 7)
        assert str(step.id) == '7'

    def test__preserves_caller_supplied_id(self):
        step = parse_step({'action': 'get_url', 'id': 'custom'}, 7)
        assert str(step.id) == 'custom'

    def test__missing_action_raises_422(self):
        with pytest.raises(HTTPException) as exc:
            parse_step({'url': 'x'}, 0)
        assert exc.value.status_code == 422
        assert 'missing required field' in exc.value.detail

    def test__unknown_action_raises_422(self):
        with pytest.raises(HTTPException) as exc:
            parse_step({'action': 'nope'}, 1)
        assert exc.value.status_code == 422
        assert 'unknown action' in exc.value.detail


class test_result_schema_for(TestCase):

    def test__typed_actions(self):
        assert result_schema_for(Enum__Step__Action.GET_CONTENT) is Schema__Step__Result__Get_Content
        assert result_schema_for(Enum__Step__Action.GET_URL    ) is Schema__Step__Result__Get_Url
        assert result_schema_for(Enum__Step__Action.EVALUATE   ) is Schema__Step__Result__Evaluate

    def test__untyped_actions_default_to_base(self):
        assert result_schema_for(Enum__Step__Action.CLICK    ) is Schema__Step__Result__Base
        assert result_schema_for(Enum__Step__Action.NAVIGATE ) is Schema__Step__Result__Base

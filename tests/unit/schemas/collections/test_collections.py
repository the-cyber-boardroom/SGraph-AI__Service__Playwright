# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Collection Subclasses (spec §6)
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest import TestCase

from sgraph_ai_service_playwright.schemas.collections.Dict__Artefacts__By_Step_Id            import Dict__Artefacts__By_Step_Id
from sgraph_ai_service_playwright.schemas.collections.Dict__Sessions__By_Id                  import Dict__Sessions__By_Id
from sgraph_ai_service_playwright.schemas.collections.Dict__Session__Browsers__By_Id         import Dict__Session__Browsers__By_Id
from sgraph_ai_service_playwright.schemas.collections.Dict__Step__Result__Schemas__By_Action import Dict__Step__Result__Schemas__By_Action
from sgraph_ai_service_playwright.schemas.collections.Dict__Step__Schemas__By_Action         import Dict__Step__Schemas__By_Action
from sgraph_ai_service_playwright.schemas.collections.List__Artefact__Refs                   import List__Artefact__Refs
from sgraph_ai_service_playwright.schemas.collections.List__Sequence__Steps                  import List__Sequence__Steps
from sgraph_ai_service_playwright.schemas.collections.List__Sessions                         import List__Sessions
from sgraph_ai_service_playwright.schemas.collections.List__Step__Results                    import List__Step__Results
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                           import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                  import Session_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Step_Id                     import Step_Id
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Info                      import Schema__Session__Info
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Click                          import Schema__Step__Click
from sgraph_ai_service_playwright.schemas.steps.Schema__Step__Navigate                       import Schema__Step__Navigate


class test_Dict__Sessions__By_Id(TestCase):

    def test__accepts_session_info(self):
        d = Dict__Sessions__By_Id()
        sid = Session_Id('s1')
        d[sid] = Schema__Session__Info()
        assert d[sid].total_actions == 0

    def test__rejects_wrong_value_type(self):
        d = Dict__Sessions__By_Id()
        with pytest.raises(Exception):
            d[Session_Id('x')] = 'not a session info'


class test_Dict__Session__Browsers__By_Id(TestCase):

    def test__accepts_any_object(self):
        d = Dict__Session__Browsers__By_Id()
        placeholder = object()
        d[Session_Id('s1')] = placeholder
        assert d[Session_Id('s1')] is placeholder


class test_Dict__Step__Schemas__By_Action(TestCase):

    def test__accepts_schema_class(self):
        d = Dict__Step__Schemas__By_Action()
        d[Enum__Step__Action.NAVIGATE] = Schema__Step__Navigate
        assert d[Enum__Step__Action.NAVIGATE] is Schema__Step__Navigate


class test_Dict__Step__Result__Schemas__By_Action(TestCase):

    def test__default_construct(self):
        assert Dict__Step__Result__Schemas__By_Action() == {}


class test_List__Sequence__Steps(TestCase):

    def test__accepts_step_subclasses(self):
        steps = List__Sequence__Steps()
        steps.append(Schema__Step__Navigate(url='https://x'))
        steps.append(Schema__Step__Click   (selector='#b'))
        assert len(steps) == 2


class test_List__Step__Results(TestCase):

    def test__default_empty(self):
        assert List__Step__Results() == []


class test_List__Artefact__Refs(TestCase):

    def test__default_empty(self):
        assert List__Artefact__Refs() == []


class test_List__Sessions(TestCase):

    def test__default_empty(self):
        assert List__Sessions() == []


class test_Dict__Artefacts__By_Step_Id(TestCase):

    def test__accepts_list_of_artefact_refs(self):
        d = Dict__Artefacts__By_Step_Id()
        d[Step_Id('step-1')] = List__Artefact__Refs()
        assert d[Step_Id('step-1')] == []

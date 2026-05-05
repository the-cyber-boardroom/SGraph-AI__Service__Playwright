# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Step Result Schemas (spec §5.7)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.playwright.core.schemas.enums.Enum__Content__Format                      import Enum__Content__Format
from sg_compute_specs.playwright.core.schemas.enums.Enum__Evaluate__Return_Type                import Enum__Evaluate__Return_Type
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Base               import Schema__Step__Result__Base
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Evaluate           import Schema__Step__Result__Evaluate
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Get_Content        import Schema__Step__Result__Get_Content
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Get_Url            import Schema__Step__Result__Get_Url


class test_Schema__Step__Result__Base(TestCase):

    def test__defaults(self):
        r = Schema__Step__Result__Base()
        assert r.duration_ms   == 0
        assert r.artefacts     == []
        assert r.error_message is None


class test_Schema__Step__Result__Get_Content(TestCase):

    def test__defaults(self):
        r = Schema__Step__Result__Get_Content()
        assert r.content_type    == 'text/html'
        assert r.content_format  is None                                            # No default in spec; set at build time

    def test__with_explicit_format(self):
        r = Schema__Step__Result__Get_Content(content_format=Enum__Content__Format.HTML)
        assert r.content_format == Enum__Content__Format.HTML

    def test__is_subclass_of_base(self):
        assert issubclass(Schema__Step__Result__Get_Content, Schema__Step__Result__Base)


class test_Schema__Step__Result__Get_Url(TestCase):

    def test__accepts_url(self):
        r = Schema__Step__Result__Get_Url(url='https://example.com/page')
        assert str(r.url) == 'https://example.com/page'


class test_Schema__Step__Result__Evaluate(TestCase):

    def test__return_value_accepts_any_json(self):
        r = Schema__Step__Result__Evaluate(return_value={'k': 1, 'l': [1, 2]},
                                           return_type=Enum__Evaluate__Return_Type.JSON)
        assert r.return_value == {'k': 1, 'l': [1, 2]}

    def test__return_value_defaults_to_none(self):
        r = Schema__Step__Result__Evaluate(return_type=Enum__Evaluate__Return_Type.JSON)
        assert r.return_value is None

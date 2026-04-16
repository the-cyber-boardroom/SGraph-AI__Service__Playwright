# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Browser Primitives
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest import TestCase

from sgraph_ai_service_playwright.schemas.primitives.browser import (
    Safe_Str__Selector                                                   ,
    Safe_Str__Browser__Launch_Arg                                        ,
    Safe_Str__JS__Expression                                             ,
)


class test_Safe_Str__Selector(TestCase):

    def test__accepts_css_selector(self):
        assert str(Safe_Str__Selector('#login-button' )) == '#login-button'
        assert str(Safe_Str__Selector('div.card > a' )) == 'div.card > a'

    def test__accepts_xpath_selector(self):
        xp = '//button[contains(text(), "Submit")]'
        assert str(Safe_Str__Selector(xp)) == xp

    def test__accepts_multiline_selector(self):                                     # DOTALL — newlines allowed
        s = 'div.card\n> a.link'
        assert str(Safe_Str__Selector(s)) == s

    def test__allows_empty_for_type_safe_default_construction(self):                # Required because Type_Safe default-constructs fields
        assert str(Safe_Str__Selector('')) == ''

    def test__rejects_overlong(self):
        with pytest.raises(ValueError):
            Safe_Str__Selector('a' * 1025)


class test_Safe_Str__Browser__Launch_Arg(TestCase):

    def test__accepts_typical_flags(self):
        assert str(Safe_Str__Browser__Launch_Arg('--disable-gpu'              )) == '--disable-gpu'
        assert str(Safe_Str__Browser__Launch_Arg('--window-size=1920,1080'    )) == '--window-size=1920,1080'
        assert str(Safe_Str__Browser__Launch_Arg('--user-data-dir=/tmp/chrome')) == '--user-data-dir=/tmp/chrome'

    def test__replaces_disallowed_chars(self):
        assert str(Safe_Str__Browser__Launch_Arg('--arg with spaces')) == '--arg_with_spaces'


class test_Safe_Str__JS__Expression(TestCase):

    def test__accepts_simple_expression(self):
        assert str(Safe_Str__JS__Expression('document.title')) == 'document.title'

    def test__accepts_multiline_expression(self):                                   # DOTALL — newlines allowed
        js = 'const x = 1;\nreturn x + 2;'
        assert str(Safe_Str__JS__Expression(js)) == js

    def test__accepts_special_chars(self):                                          # No character allowlist at primitive layer
        js = '() => { return "<foo>&bar"; }'
        assert str(Safe_Str__JS__Expression(js)) == js

    def test__allows_empty_for_type_safe_default_construction(self):                # Required because Type_Safe default-constructs fields
        assert str(Safe_Str__JS__Expression('')) == ''

    def test__rejects_overlong(self):
        with pytest.raises(ValueError):
            Safe_Str__JS__Expression('a' * 4097)

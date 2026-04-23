# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Safe_Str__Stack__Name
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                                                   import TestCase
import pytest

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__Stack__Name                           import Safe_Str__Stack__Name


class test_Safe_Str__Stack__Name(TestCase):

    def test__accepts_valid_names(self):
        assert str(Safe_Str__Stack__Name('sp-observe-1'  )) == 'sp-observe-1'
        assert str(Safe_Str__Stack__Name('sp-observe-prod')) == 'sp-observe-prod'
        assert str(Safe_Str__Stack__Name('abc'           )) == 'abc'                # Minimum length boundary

    def test__lowercases_input(self):
        assert str(Safe_Str__Stack__Name('SP-Observe-1')) == 'sp-observe-1'

    def test__rejects_leading_digit(self):                                          # AWS OpenSearch domains must start with a letter
        with pytest.raises(ValueError):
            Safe_Str__Stack__Name('1bad-name')

    def test__rejects_underscore(self):                                             # AWS OpenSearch domains forbid underscores
        with pytest.raises(ValueError):
            Safe_Str__Stack__Name('bad_name')

    def test__rejects_too_short(self):
        with pytest.raises(ValueError):
            Safe_Str__Stack__Name('ab')                                             # Below 3-char minimum

    def test__rejects_too_long(self):
        with pytest.raises(ValueError):
            Safe_Str__Stack__Name('a' + 'b' * 28)                                   # 29 chars exceeds 28-char limit

    def test__accepts_empty(self):                                                  # Auto-init support; real validation happens on non-empty values
        assert str(Safe_Str__Stack__Name('')) == ''

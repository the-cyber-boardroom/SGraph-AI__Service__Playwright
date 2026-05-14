# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__Slug (no mocks, no patches)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from vault_publish.schemas.Safe_Str__Slug import Safe_Str__Slug


class test_Safe_Str__Slug(TestCase):

    def test_accepts_valid_slug(self):
        assert str(Safe_Str__Slug('sara-cv'))            == 'sara-cv'
        assert str(Safe_Str__Slug('demo-health-score'))  == 'demo-health-score'
        assert str(Safe_Str__Slug('abc'))                == 'abc'
        assert str(Safe_Str__Slug('a1b2'))               == 'a1b2'

    def test_allows_empty(self):                                             # response schemas default-construct
        assert str(Safe_Str__Slug('')) == ''
        assert str(Safe_Str__Slug())   == ''

    def test_rejects_uppercase(self):
        with self.assertRaises(ValueError):
            Safe_Str__Slug('Sara-CV')

    def test_rejects_underscore_and_space(self):
        with self.assertRaises(ValueError):
            Safe_Str__Slug('sara_cv')
        with self.assertRaises(ValueError):
            Safe_Str__Slug('sara cv')

    def test_rejects_over_max_length(self):
        with self.assertRaises(ValueError):
            Safe_Str__Slug('a' * 41)

    def test_accepts_max_length(self):
        assert len(str(Safe_Str__Slug('a' * 40))) == 40

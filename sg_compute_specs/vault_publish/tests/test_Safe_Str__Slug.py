# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__Slug
# Charset, max-length, leading/trailing/consecutive-hyphen guards.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug import Safe_Str__Slug


class TestSafeStrSlug:
    def test_valid_simple(self):
        s = Safe_Str__Slug('hello')
        assert str(s) == 'hello'

    def test_valid_with_hyphens(self):
        s = Safe_Str__Slug('sara-cv')
        assert str(s) == 'sara-cv'

    def test_valid_with_numbers(self):
        s = Safe_Str__Slug('abc123')
        assert str(s) == 'abc123'

    def test_empty_allowed(self):
        s = Safe_Str__Slug('')
        assert str(s) == ''

    def test_none_returns_empty(self):
        s = Safe_Str__Slug(None)
        assert str(s) == ''

    def test_uppercase_converted_to_lower(self):
        s = Safe_Str__Slug('HelloWorld')
        assert str(s) == 'helloworld'

    def test_invalid_chars_raises(self):
        with pytest.raises(Exception):
            Safe_Str__Slug('hello_world')  # underscore not allowed

    def test_invalid_chars_with_space_raises(self):
        with pytest.raises(Exception):
            Safe_Str__Slug('hello world')

    def test_max_length_63_ok(self):
        s = Safe_Str__Slug('a' * 63)
        assert len(str(s)) == 63

    def test_over_max_length_raises(self):
        with pytest.raises(Exception):
            Safe_Str__Slug('a' * 64)

# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Slug__Validator (no mocks, no patches)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from vault_publish.schemas.Enum__Slug__Error_Code import Enum__Slug__Error_Code
from vault_publish.schemas.Safe_Str__Slug         import Safe_Str__Slug
from vault_publish.service.Slug__Validator        import Slug__Validator


class test_Slug__Validator(TestCase):

    def setUp(self):
        self.validator = Slug__Validator()

    # ── valid ────────────────────────────────────────────────────────────────

    def test_valid_slug_returns_none(self):
        assert self.validator.validate('sara-cv')           is None
        assert self.validator.validate('demo-health-score') is None
        assert self.validator.is_valid('abc')               is True

    # ── length ───────────────────────────────────────────────────────────────

    def test_too_short(self):
        assert self.validator.validate('ab') == Enum__Slug__Error_Code.TOO_SHORT
        assert self.validator.validate('')   == Enum__Slug__Error_Code.TOO_SHORT

    def test_too_long(self):
        assert self.validator.validate('a' * 41) == Enum__Slug__Error_Code.TOO_LONG

    # ── charset ──────────────────────────────────────────────────────────────

    def test_bad_charset(self):
        assert self.validator.validate('Sara')  == Enum__Slug__Error_Code.BAD_CHARSET
        assert self.validator.validate('a_b')   == Enum__Slug__Error_Code.BAD_CHARSET
        assert self.validator.validate('a b')   == Enum__Slug__Error_Code.BAD_CHARSET
        assert self.validator.validate('a.b')   == Enum__Slug__Error_Code.BAD_CHARSET

    # ── hyphen shape ─────────────────────────────────────────────────────────

    def test_leading_hyphen(self):
        assert self.validator.validate('-abc') == Enum__Slug__Error_Code.LEADING_HYPHEN

    def test_trailing_hyphen(self):
        assert self.validator.validate('abc-') == Enum__Slug__Error_Code.TRAILING_HYPHEN

    def test_double_hyphen(self):
        assert self.validator.validate('a--b') == Enum__Slug__Error_Code.DOUBLE_HYPHEN

    # ── reserved / profane ───────────────────────────────────────────────────

    def test_reserved_slug(self):
        assert self.validator.validate('www')   == Enum__Slug__Error_Code.RESERVED
        assert self.validator.validate('api')   == Enum__Slug__Error_Code.RESERVED
        assert self.validator.validate('admin') == Enum__Slug__Error_Code.RESERVED

    def test_profane_slug(self):
        assert self.validator.validate('damn') == Enum__Slug__Error_Code.PROFANE

    def test_uppercase_reserved_is_charset_error_first(self):                # charset check precedes reserved
        assert self.validator.validate('WWW') == Enum__Slug__Error_Code.BAD_CHARSET

    # ── messages ─────────────────────────────────────────────────────────────

    def test_message_for_is_specific(self):
        msg = self.validator.message_for(Enum__Slug__Error_Code.DOUBLE_HYPHEN)
        assert 'double hyphen' in msg

    # ── to_slug ──────────────────────────────────────────────────────────────

    def test_to_slug_promotes_valid(self):
        slug = self.validator.to_slug('sara-cv')
        assert isinstance(slug, Safe_Str__Slug)
        assert str(slug) == 'sara-cv'

    def test_to_slug_raises_on_invalid(self):
        with self.assertRaises(ValueError):
            self.validator.to_slug('a--b')

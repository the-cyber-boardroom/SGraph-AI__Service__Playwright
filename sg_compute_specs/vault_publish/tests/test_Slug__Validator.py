# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Slug__Validator
# Every error code path + the happy path.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_publish.schemas.Enum__Slug__Error_Code import Enum__Slug__Error_Code
from sg_compute_specs.vault_publish.service.Slug__Validator         import Slug__Validator


class TestSlugValidator:
    def setup_method(self):
        self.v = Slug__Validator()

    def test_valid_slug_returns_none(self):
        assert self.v.validate('sara-cv')    is None
        assert self.v.validate('hello')      is None
        assert self.v.validate('abc123')     is None
        assert self.v.validate('my-project') is None

    def test_empty_slug_returns_empty(self):
        assert self.v.validate('') == Enum__Slug__Error_Code.EMPTY

    def test_invalid_charset_uppercase(self):
        assert self.v.validate('Hello') == Enum__Slug__Error_Code.INVALID_CHARSET

    def test_invalid_charset_underscore(self):
        assert self.v.validate('hello_world') == Enum__Slug__Error_Code.INVALID_CHARSET

    def test_invalid_charset_dot(self):
        assert self.v.validate('hello.world') == Enum__Slug__Error_Code.INVALID_CHARSET

    def test_too_long(self):
        assert self.v.validate('a' * 64) == Enum__Slug__Error_Code.TOO_LONG

    def test_max_length_ok(self):
        assert self.v.validate('a' * 63) is None

    def test_leading_hyphen(self):
        assert self.v.validate('-hello') == Enum__Slug__Error_Code.LEADING_HYPHEN

    def test_trailing_hyphen(self):
        assert self.v.validate('hello-') == Enum__Slug__Error_Code.TRAILING_HYPHEN

    def test_consecutive_hyphens(self):
        assert self.v.validate('hello--world') == Enum__Slug__Error_Code.CONSECUTIVE_HYPHENS

    def test_reserved_www(self):
        assert self.v.validate('www') == Enum__Slug__Error_Code.RESERVED

    def test_reserved_api(self):
        assert self.v.validate('api') == Enum__Slug__Error_Code.RESERVED

    def test_reserved_admin(self):
        assert self.v.validate('admin') == Enum__Slug__Error_Code.RESERVED

    def test_reserved_status(self):
        assert self.v.validate('status') == Enum__Slug__Error_Code.RESERVED

    def test_reserved_mail(self):
        assert self.v.validate('mail') == Enum__Slug__Error_Code.RESERVED

    def test_reserved_cdn(self):
        assert self.v.validate('cdn') == Enum__Slug__Error_Code.RESERVED

    def test_reserved_auth(self):
        assert self.v.validate('auth') == Enum__Slug__Error_Code.RESERVED

    def test_non_reserved_word_passes(self):
        assert self.v.validate('sara-cv')  is None
        assert self.v.validate('my-vault') is None

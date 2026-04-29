# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Safe_Str__Vnc__Password
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__Vnc__Password       import Safe_Str__Vnc__Password


class test_Safe_Str__Vnc__Password(TestCase):

    def test__valid_passwords__url_safe(self):                                       # Auto-generated shape (secrets.token_urlsafe)
        for ok in ('AAAA-BBBB-1234-cdef', 'YYYYZZZZ_1234567890abc', 'a' * 16, 'Z9_-' * 4):
            assert str(Safe_Str__Vnc__Password(ok)) == ok

    def test__valid_passwords__operator_supplied_with_special_chars(self):           # Relaxed: any printable ASCII except single quote
        for ok in ('abc@@12', 'P@ssw0rd!', '!@#$%^&*()_+={}[]', 'has"double"quotes',
                   'short', 'with`backticks`', 'with\\backslash', 'a' * 128):
            assert str(Safe_Str__Vnc__Password(ok)) == ok

    def test__rejects_below_min_length(self):
        with self.assertRaises(ValueError):
            Safe_Str__Vnc__Password('abc')                                            # 3 chars; min is 4

    def test__rejects_above_max_length(self):
        with self.assertRaises(ValueError):
            Safe_Str__Vnc__Password('a' * 129)

    def test__rejects_single_quote(self):                                             # Would break the user-data shell escaping
        with self.assertRaises(ValueError):
            Safe_Str__Vnc__Password("has'quote12")

    def test__rejects_whitespace(self):                                               # Trimmed at construction; embedded space rejected
        for bad in ('has space12', 'tab\there12', 'newline\n12'):
            with self.assertRaises(ValueError):
                Safe_Str__Vnc__Password(bad)

    def test__rejects_non_ascii(self):
        with self.assertRaises(ValueError):
            Safe_Str__Vnc__Password('café-1234')

    def test__empty_allowed(self):                                                    # Service rejects empty on create; auto-init friendliness
        assert str(Safe_Str__Vnc__Password('')) == ''

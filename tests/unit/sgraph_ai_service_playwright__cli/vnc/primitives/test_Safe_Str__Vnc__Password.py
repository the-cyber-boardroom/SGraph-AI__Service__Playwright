# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Safe_Str__Vnc__Password
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__Vnc__Password       import Safe_Str__Vnc__Password


class test_Safe_Str__Vnc__Password(TestCase):

    def test__valid_passwords(self):
        for ok in ('AAAA-BBBB-1234-cdef', 'YYYYZZZZ_1234567890abc', 'a' * 16, 'Z9_-' * 4):
            assert str(Safe_Str__Vnc__Password(ok)) == ok

    def test__rejects_too_short(self):
        with self.assertRaises(ValueError):
            Safe_Str__Vnc__Password('a' * 15)

    def test__rejects_non_url_safe_chars(self):
        for bad in ('a' * 16 + '!', 'has space123456', 'has/slash1234567'):
            with self.assertRaises(ValueError):
                Safe_Str__Vnc__Password(bad)

    def test__empty_allowed(self):                                                  # Service rejects empty on create; auto-init friendliness
        assert str(Safe_Str__Vnc__Password('')) == ''

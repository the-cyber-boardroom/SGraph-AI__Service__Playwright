# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Safe_Str__OS__Password
# Mirrors the elastic password primitive — same regex, same length bounds.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.primitives.Safe_Str__OS__Password import Safe_Str__OS__Password


class test_Safe_Str__OS__Password(TestCase):

    def test__valid_password(self):                                                 # secrets.token_urlsafe-style
        assert str(Safe_Str__OS__Password('AAAA-BBBB-1234-cdef')) == 'AAAA-BBBB-1234-cdef'

    def test__empty_allowed(self):                                                  # allow_empty=True for the Info schema
        assert str(Safe_Str__OS__Password('')) == ''

    def test__rejects_too_short(self):                                              # Min 16 chars
        with self.assertRaises(ValueError):
            Safe_Str__OS__Password('short')

    def test__rejects_too_long(self):                                               # Max 64 chars
        with self.assertRaises(ValueError):
            Safe_Str__OS__Password('a' * 65)

    def test__rejects_disallowed_chars(self):                                       # Only A-Z a-z 0-9 _ -
        with self.assertRaises(ValueError):
            Safe_Str__OS__Password('hello+world+with+plus')

    def test__matches_elastic_password_regex(self):                                 # Same shape as elastic — drift would surprise users
        from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Password import Safe_Str__Elastic__Password
        assert Safe_Str__OS__Password.regex.pattern == Safe_Str__Elastic__Password.regex.pattern

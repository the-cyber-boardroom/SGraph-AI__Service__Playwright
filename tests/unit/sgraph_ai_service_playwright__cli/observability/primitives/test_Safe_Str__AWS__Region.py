# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Safe_Str__AWS__Region
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                                                   import TestCase
import pytest

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region                           import Safe_Str__AWS__Region


class test_Safe_Str__AWS__Region(TestCase):

    def test__accepts_common_regions(self):
        assert str(Safe_Str__AWS__Region('eu-west-2'      )) == 'eu-west-2'
        assert str(Safe_Str__AWS__Region('us-east-1'      )) == 'us-east-1'
        assert str(Safe_Str__AWS__Region('ap-southeast-1' )) == 'ap-southeast-1'

    def test__allows_empty(self):                                                   # Empty = "resolve at runtime"
        assert str(Safe_Str__AWS__Region('')) == ''

    def test__replaces_invalid_chars(self):                                       # canonical uses REPLACE mode (not STRICT) so shell-quote stripping works
        # Underscore is not in [a-z0-9-] and gets replaced with '_' (default
        # replacement char) — a no-op for underscores but visible for other
        # punctuation. Shape validation is the caller's concern; Safe_Str only
        # guarantees character safety. See Aws__Region__Resolver._env_region
        # for the matching shell-quote-strip flow that relies on this.
        assert str(Safe_Str__AWS__Region("'eu-west-2'")) == '_eu-west-2_'
        assert str(Safe_Str__AWS__Region('eu_west_2'))  == 'eu_west_2'           # underscore→underscore (default replacement char)

# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — CF__Realtime__Log__Parser module-level helpers
# Pins each tiny conversion in isolation so the parser tests can focus on
# the orchestration layer (TSV row → Schema__CF__Event__Record).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Edge__Result__Type  import Enum__CF__Edge__Result__Type
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Status__Class       import Enum__CF__Status__Class
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import (
    CACHE_HIT_RESULT_TYPES,
    clean_referer,
    clean_user_agent,
    gunzip,
    normalise_country,
    normalise_edge_location,
    normalise_cipher,
    parse_dash_or,
    parse_int_or,
    parse_seconds_to_ms,
    parse_unix_to_iso,
    safe_enum,
    status_class_from_int,
)


class test_parse_unix_to_iso(TestCase):

    def test_real_cf_timestamp(self):                                               # Real value from the user's pasted CF log line
        assert parse_unix_to_iso('1777075217.167') == '2026-04-25T00:00:17.167Z'

    def test_zero_millis(self):
        assert parse_unix_to_iso('1777075217.000') == '2026-04-25T00:00:17.000Z'

    def test_invalid_returns_empty(self):
        assert parse_unix_to_iso('not-a-number') == ''
        assert parse_unix_to_iso('') == ''


class test_parse_seconds_to_ms(TestCase):

    def test_basic_conversions(self):
        assert parse_seconds_to_ms('0.001') == 1                                    # 1 ms
        assert parse_seconds_to_ms('0.924') == 924
        assert parse_seconds_to_ms('1.000') == 1000

    def test_dash_returns_default(self):
        assert parse_seconds_to_ms('-')        == 0
        assert parse_seconds_to_ms('-', -1)    == -1

    def test_empty_returns_default(self):
        assert parse_seconds_to_ms('')         == 0


class test_parse_int_or(TestCase):

    def test_valid(self):
        assert parse_int_or('302') == 302
        assert parse_int_or('0')   == 0

    def test_dash_returns_default(self):
        assert parse_int_or('-')         == 0
        assert parse_int_or('-', -1)     == -1

    def test_garbage_returns_default(self):
        assert parse_int_or('abc')       == 0


class test_parse_dash_or(TestCase):

    def test_dash_becomes_empty(self):
        assert parse_dash_or('-') == ''

    def test_empty_stays_empty(self):
        assert parse_dash_or('') == ''

    def test_value_unchanged(self):
        assert parse_dash_or('hello') == 'hello'


class test_status_class_from_int(TestCase):

    def test_each_class(self):
        assert status_class_from_int(100) == Enum__CF__Status__Class.INFORMATIONAL
        assert status_class_from_int(200) == Enum__CF__Status__Class.SUCCESS
        assert status_class_from_int(302) == Enum__CF__Status__Class.REDIRECTION
        assert status_class_from_int(404) == Enum__CF__Status__Class.CLIENT_ERROR
        assert status_class_from_int(500) == Enum__CF__Status__Class.SERVER_ERROR

    def test_outside_range(self):
        assert status_class_from_int(0)    == Enum__CF__Status__Class.OTHER
        assert status_class_from_int(999)  == Enum__CF__Status__Class.OTHER
        assert status_class_from_int(-1)   == Enum__CF__Status__Class.OTHER


class test_safe_enum(TestCase):

    def test_known_value(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Method import Enum__CF__Method
        assert safe_enum(Enum__CF__Method, 'GET', Enum__CF__Method.OTHER) == Enum__CF__Method.GET

    def test_dash_returns_default(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Method import Enum__CF__Method
        assert safe_enum(Enum__CF__Method, '-', Enum__CF__Method.OTHER) == Enum__CF__Method.OTHER

    def test_unknown_returns_default(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Method import Enum__CF__Method
        assert safe_enum(Enum__CF__Method, 'PROPFIND', Enum__CF__Method.OTHER) == Enum__CF__Method.OTHER


class test_clean_user_agent(TestCase):

    def test_url_decode(self):                                                      # Real CF UA with %20-encoded spaces
        encoded = 'Mozilla/5.0%20(compatible;%20wpbot/1.4;%20+https://forms.gle/foo)'
        decoded = 'Mozilla/5.0 (compatible; wpbot/1.4; +https://forms.gle/foo)'
        assert clean_user_agent(encoded) == decoded

    def test_dash_returns_empty(self):
        assert clean_user_agent('-') == ''

    def test_caps_at_500(self):
        long_ua = 'A' * 600
        assert len(clean_user_agent(long_ua)) == 500


class test_clean_referer(TestCase):

    def test_strips_query_string(self):
        assert clean_referer('https://example.com/page?foo=bar&baz=1') == 'https://example.com/page'

    def test_dash_returns_empty(self):
        assert clean_referer('-') == ''

    def test_no_query_unchanged(self):
        assert clean_referer('https://example.com/page') == 'https://example.com/page'


class test_normalisers(TestCase):

    def test_country_uppercased(self):                                              # Parser must uppercase before constructing Safe_Str__CF__Country
        assert normalise_country('us') == 'US'
        assert normalise_country('-')  == ''

    def test_edge_location_uppercased(self):
        assert normalise_edge_location('hio52-p4') == 'HIO52-P4'

    def test_cipher_uppercased(self):
        assert normalise_cipher('tls_aes_128_gcm_sha256') == 'TLS_AES_128_GCM_SHA256'


class test_cache_hit_set(TestCase):

    def test_three_members(self):                                                   # Hit / RefreshHit / OriginShieldHit count as cache hits
        assert Enum__CF__Edge__Result__Type.Hit             in CACHE_HIT_RESULT_TYPES
        assert Enum__CF__Edge__Result__Type.RefreshHit      in CACHE_HIT_RESULT_TYPES
        assert Enum__CF__Edge__Result__Type.OriginShieldHit in CACHE_HIT_RESULT_TYPES

    def test_function_response_NOT_cache_hit(self):                                 # FunctionGeneratedResponse is generated by edge but not from cache
        assert Enum__CF__Edge__Result__Type.FunctionGeneratedResponse not in CACHE_HIT_RESULT_TYPES
        assert Enum__CF__Edge__Result__Type.Miss                       not in CACHE_HIT_RESULT_TYPES
        assert Enum__CF__Edge__Result__Type.Error                      not in CACHE_HIT_RESULT_TYPES


class test_gunzip(TestCase):

    def test_round_trip(self):
        import gzip
        original   = 'hello\nworld\n'
        compressed = gzip.compress(original.encode('utf-8'))
        assert gunzip(compressed) == original

    def test_empty_bytes_returns_empty_string(self):
        assert gunzip(b'') == ''

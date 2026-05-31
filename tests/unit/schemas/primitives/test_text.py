# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Text Primitives (Safe_Str__Url__Permissive)
#
# BUG-1 (debrief 2026-05-30): osbot-utils Safe_Str__Url rejects ':' (and other
# RFC 3986 pchar characters) from the fragment class, breaking vault-key-in-URL
# workflows. Our Safe_Str__Url__Permissive is the RFC-compliant replacement.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest import TestCase

from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Url__Permissive  import Safe_Str__Url__Permissive


class test_Safe_Str__Url__Permissive(TestCase):

    # ── BUG-1 — the regression the report flagged ────────────────────────────

    def test__accepts_colon_in_fragment__the_bug_1_repro(self):                     # the exact shape that crashed the previous build
        u = 'https://dev.vault.sgraph.ai/#tcss7to5vfp6asjbm1t1p5ng:rqw3wk4b'
        assert str(Safe_Str__Url__Permissive(u)) == u

    def test__accepts_at_sign_in_fragment(self):
        assert str(Safe_Str__Url__Permissive('https://x.example/#user@host')) == 'https://x.example/#user@host'

    def test__accepts_pchar_sub_delims_in_fragment(self):                           # ! $ & ' ( ) * + , ; =
        u = "https://x.example/#a!b$c&d'e(f)g*h+i,j;k=l"
        assert str(Safe_Str__Url__Permissive(u)) == u

    def test__accepts_slash_and_query_marker_in_fragment(self):
        u = 'https://x.example/#path/in/fragment?q=1'
        assert str(Safe_Str__Url__Permissive(u)) == u

    # ── ordinary URLs still work ─────────────────────────────────────────────

    def test__accepts_plain_https(self):
        assert str(Safe_Str__Url__Permissive('https://example.com')) == 'https://example.com'

    def test__accepts_http_with_port_and_path(self):
        u = 'http://localhost:8080/api/info/versions'
        assert str(Safe_Str__Url__Permissive(u)) == u

    def test__accepts_query_with_pchar(self):
        u = 'https://example.com/search?q=hello+world&lang=en-GB'
        assert str(Safe_Str__Url__Permissive(u)) == u

    def test__accepts_percent_encoded_fragment(self):                               # the workaround the report mentions still works
        u = 'https://dev.vault.sgraph.ai/#tcss7to5vfp6asjbm1t1p5ng%3Arqw3wk4b'
        assert str(Safe_Str__Url__Permissive(u)) == u

    def test__allows_empty_for_type_safe_default_construction(self):
        assert str(Safe_Str__Url__Permissive('')) == ''

    # ── still rejects clearly-not-URLs ───────────────────────────────────────

    def test__rejects_missing_scheme(self):
        with pytest.raises(ValueError):
            Safe_Str__Url__Permissive('example.com/x')

    def test__rejects_non_http_scheme(self):
        with pytest.raises(ValueError):
            Safe_Str__Url__Permissive('ftp://example.com/')

    def test__rejects_whitespace(self):
        with pytest.raises(ValueError):
            Safe_Str__Url__Permissive('https://example.com/ has space')

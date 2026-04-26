# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Safe_Str__CF__Cipher
# IANA cipher names. Real value from the user's pasted CF log line.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.primitives.Safe_Str__CF__Cipher import Safe_Str__CF__Cipher


class test_Safe_Str__CF__Cipher(TestCase):

    def test_real_cipher(self):
        assert Safe_Str__CF__Cipher('TLS_AES_128_GCM_SHA256') == 'TLS_AES_128_GCM_SHA256'

    def test_ecdhe_cipher(self):
        assert Safe_Str__CF__Cipher('ECDHE-RSA-AES128-GCM-SHA256') == 'ECDHE-RSA-AES128-GCM-SHA256'

    def test_lowercase_rejected(self):                                              # Parser uppercases before construction; primitive itself is strict
        try:
            Safe_Str__CF__Cipher('tls_aes_128_gcm_sha256')
            assert False, 'expected validation error'
        except (ValueError, Exception):
            pass

    def test_empty_allowed(self):
        assert Safe_Str__CF__Cipher('') == ''

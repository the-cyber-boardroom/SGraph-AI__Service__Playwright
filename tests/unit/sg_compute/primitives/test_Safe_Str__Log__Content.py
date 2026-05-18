# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__Log__Content (v0.2.30 / Open-5 Part 2)
#
# Pins the alphabet of the log-capture primitive so a future change can't
# silently regress to the Safe_Str default that strips colons, parens,
# newlines, etc. — same default-regex shape as the SignatureDoesNotMatch
# credential bug fixed on 2026-05-17.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.primitives.Safe_Str__Log__Content import Safe_Str__Log__Content


class test_Safe_Str__Log__Content(TestCase):

    def test__multiline_log_with_special_chars_round_trips(self):
        log = 'INFO: started\nERROR: failed at line 42 (timeout: 30s)\n'
        assert str(Safe_Str__Log__Content(log)) == log

    def test__binary_garbage_scrubbed(self):
        assert str(Safe_Str__Log__Content('hello\x00\x01world')) == 'hello__world'

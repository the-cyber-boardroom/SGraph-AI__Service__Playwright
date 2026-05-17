# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__Message (v0.2.30 / Open-5 Part 2)
#
# Pins the alphabet of the 512-char status-message primitive so a future
# change can't silently regress to the Safe_Str default that mangles
# : = / % - in realistic status text.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.primitives.Safe_Str__Message import Safe_Str__Message


class test_Safe_Str__Message(TestCase):

    def test__status_message_with_special_chars_round_trips(self):
        msg = 'CloudFront E123ABC: status=disabled / 4xx-rate=12%'
        assert str(Safe_Str__Message(msg)) == msg

# ═══════════════════════════════════════════════════════════════════════════════
# ephemeral_ec2 tests — Health__HTTP__Probe
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from ephemeral_ec2.helpers.health.Health__HTTP__Probe import Health__HTTP__Probe


class test_Health__HTTP__Probe(TestCase):

    def test_check__unreachable_returns_false(self):
        probe = Health__HTTP__Probe()
        assert probe.check('https://127.0.0.1:19999/health', timeout_sec=2) is False

    def test_check__invalid_url_returns_false(self):
        probe = Health__HTTP__Probe()
        assert probe.check('https://this-host-does-not-exist-xyz.invalid/', timeout_sec=2) is False

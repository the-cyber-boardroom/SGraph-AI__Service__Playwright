# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Safe_Str__Aws_Usage_Type (v0.2.30 / Open-5 Part 2)
#
# Pins the alphabet for Cost Explorer usage-type strings ('EU-BoxUsage:t3.micro')
# so a future change can't silently regress to the Safe_Str default that
# mangles the colon and dot — same default-regex shape as the
# SignatureDoesNotMatch credential bug fixed on 2026-05-17.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.billing.primitives.Safe_Str__Aws_Usage_Type import Safe_Str__Aws_Usage_Type


class test_Safe_Str__Aws_Usage_Type(TestCase):

    def test__cost_explorer_usage_type_round_trips(self):
        usage = 'EU-BoxUsage:t3.micro'
        assert str(Safe_Str__Aws_Usage_Type(usage)) == usage

    def test__other_realistic_shapes(self):
        for raw in ['DataTransfer-Out-Bytes', 'Requests-Tier1', 'EUW2-BoxUsage:t4g.nano']:
            assert str(Safe_Str__Aws_Usage_Type(raw)) == raw

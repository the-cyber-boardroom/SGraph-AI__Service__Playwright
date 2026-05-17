# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Logs__Time__Parser
# Covers: relative expressions, absolute ISO 8601, bad inputs, defaults.
# ═══════════════════════════════════════════════════════════════════════════════

import time

import pytest

from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__Time__Parser import Logs__Time__Parser


class TestRelativeExpressions:

    def test_seconds(self):
        tp  = Logs__Time__Parser()
        now = tp.now_ms()
        ts  = tp.parse('30s')
        assert abs(ts - (now - 30_000)) < 100

    def test_minutes(self):
        tp  = Logs__Time__Parser()
        now = tp.now_ms()
        ts  = tp.parse('5m')
        assert abs(ts - (now - 300_000)) < 100

    def test_hours(self):
        tp  = Logs__Time__Parser()
        now = tp.now_ms()
        ts  = tp.parse('2h')
        assert abs(ts - (now - 7_200_000)) < 200

    def test_days(self):
        tp  = Logs__Time__Parser()
        now = tp.now_ms()
        ts  = tp.parse('1d')
        assert abs(ts - (now - 86_400_000)) < 200

    def test_one_hour_default(self):
        tp  = Logs__Time__Parser()
        now = tp.now_ms()
        ts  = tp.parse_optional(None)
        assert abs(ts - (now - 3_600_000)) < 200


class TestAbsoluteExpressions:

    def test_iso_utc(self):
        tp = Logs__Time__Parser()
        ts = tp.parse('2026-05-17T14:00:00Z')
        assert ts == 1779026400000          # epoch ms for 2026-05-17T14:00:00 UTC

    def test_no_z_suffix_raises(self):
        tp = Logs__Time__Parser()
        with pytest.raises(ValueError, match='UTC'):
            tp.parse('2026-05-17T14:00:00')


class TestBadInput:

    def test_unknown_unit_raises(self):
        tp = Logs__Time__Parser()
        with pytest.raises(ValueError):
            tp.parse('10x')

    def test_empty_string_raises(self):
        tp = Logs__Time__Parser()
        with pytest.raises(ValueError):
            tp.parse('')

    def test_parse_optional_with_value(self):
        tp  = Logs__Time__Parser()
        now = tp.now_ms()
        ts  = tp.parse_optional('10m')
        assert abs(ts - (now - 600_000)) < 200

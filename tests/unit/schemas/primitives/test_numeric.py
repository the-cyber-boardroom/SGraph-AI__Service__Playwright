# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Numeric Primitives
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest import TestCase

from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Milliseconds          import Safe_UInt__Milliseconds
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Timeout_MS            import Safe_UInt__Timeout_MS
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Session_Lifetime_MS   import Safe_UInt__Session_Lifetime_MS
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Viewport_Dimension    import Safe_UInt__Viewport_Dimension
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Memory_MB             import Safe_UInt__Memory_MB


class test_Safe_UInt__Milliseconds(TestCase):

    def test__accepts_zero(self):
        assert int(Safe_UInt__Milliseconds(0)) == 0

    def test__accepts_lambda_ceiling(self):
        assert int(Safe_UInt__Milliseconds(900_000)) == 900_000

    def test__rejects_above_ceiling(self):
        with pytest.raises(ValueError):
            Safe_UInt__Milliseconds(900_001)


class test_Safe_UInt__Timeout_MS(TestCase):

    def test__accepts_typical_value(self):
        assert int(Safe_UInt__Timeout_MS(5000)) == 5000

    def test__accepts_ceiling(self):
        assert int(Safe_UInt__Timeout_MS(300_000)) == 300_000

    def test__rejects_above_ceiling(self):
        with pytest.raises(ValueError):
            Safe_UInt__Timeout_MS(300_001)


class test_Safe_UInt__Session_Lifetime_MS(TestCase):

    def test__accepts_zero(self):
        assert int(Safe_UInt__Session_Lifetime_MS(0)) == 0

    def test__accepts_four_hours(self):
        assert int(Safe_UInt__Session_Lifetime_MS(14_400_000)) == 14_400_000

    def test__rejects_above_ceiling(self):
        with pytest.raises(ValueError):
            Safe_UInt__Session_Lifetime_MS(14_400_001)


class test_Safe_UInt__Viewport_Dimension(TestCase):

    def test__accepts_typical_values(self):
        assert int(Safe_UInt__Viewport_Dimension(1280)) == 1280
        assert int(Safe_UInt__Viewport_Dimension(720 )) == 720

    def test__rejects_below_floor(self):
        with pytest.raises(ValueError):
            Safe_UInt__Viewport_Dimension(99)

    def test__rejects_above_ceiling(self):
        with pytest.raises(ValueError):
            Safe_UInt__Viewport_Dimension(4097)


class test_Safe_UInt__Memory_MB(TestCase):

    def test__accepts_typical_values(self):
        assert int(Safe_UInt__Memory_MB(512 )) == 512
        assert int(Safe_UInt__Memory_MB(2048)) == 2048

    def test__rejects_below_floor(self):
        with pytest.raises(ValueError):
            Safe_UInt__Memory_MB(127)

    def test__accepts_fargate_max(self):
        assert int(Safe_UInt__Memory_MB(30_720)) == 30_720

    def test__rejects_above_ceiling(self):
        with pytest.raises(ValueError):
            Safe_UInt__Memory_MB(30_721)

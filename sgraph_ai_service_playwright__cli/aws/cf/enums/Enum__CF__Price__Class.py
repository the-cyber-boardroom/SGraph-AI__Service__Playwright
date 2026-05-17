# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__CF__Price__Class
# CloudFront PriceClass values controlling which edge-location tiers are used.
# PriceClass_100 = US/EU/Israel; PriceClass_200 = + Asia; PriceClass_All = global.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__CF__Price__Class(str, Enum):
    PriceClass_100 = 'PriceClass_100'
    PriceClass_200 = 'PriceClass_200'
    PriceClass_All = 'PriceClass_All'

    def __str__(self):
        return self.value

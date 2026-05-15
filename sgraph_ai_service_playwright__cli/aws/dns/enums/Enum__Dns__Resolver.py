# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Dns__Resolver
# Curated set of well-known public DNS resolvers.
# The first 6 (CLOUDFLARE_1 through ADGUARD_EU) form the smart-verify set
# for new-name checks. OPENDNS_1 and OPENDNS_2 are reserved for P1.5 extended mode.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Dns__Resolver(Enum):
    CLOUDFLARE_1 = '1.1.1.1'
    CLOUDFLARE_2 = '1.0.0.1'
    GOOGLE_1     = '8.8.8.8'
    GOOGLE_2     = '8.8.4.4'
    QUAD9        = '9.9.9.9'
    ADGUARD_EU   = '94.140.14.14'
    # The following 2 are reserved for P1.5 extended mode:
    OPENDNS_1    = '208.67.222.222'
    OPENDNS_2    = '208.67.220.220'

    def __str__(self):
        return self.value

# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Route53__Record_Type
# DNS record types supported by Route 53. Used on Schema__Route53__Record and
# as a filter argument on records get / list.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Route53__Record_Type(str, Enum):
    A     = 'A'
    AAAA  = 'AAAA'
    CNAME = 'CNAME'
    MX    = 'MX'
    TXT   = 'TXT'
    NS    = 'NS'
    SOA   = 'SOA'
    PTR   = 'PTR'
    SRV   = 'SRV'
    CAA   = 'CAA'

    def __str__(self):
        return self.value

# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Slug__From_Host
# Parses a Host header value to extract the vault-publish slug.
# Zone apex is read from SG_AWS__DNS__DEFAULT_ZONE (default: aws.sg-labs.app).
# Returns the Safe_Str__Slug or None if the host doesn't match the zone.
#
# Example: 'sara-cv.aws.sg-labs.app' → Safe_Str__Slug('sara-cv')
#          'unknown.example.com'     → None
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing import Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug import Safe_Str__Slug

_ZONE_FALLBACK = 'aws.sg-labs.app'


def _zone_apex() -> str:
    return os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', _ZONE_FALLBACK)


class Slug__From_Host(Type_Safe):

    def extract(self, host: str) -> Optional[Safe_Str__Slug]:
        host  = (host or '').strip().rstrip('.')
        zone  = _zone_apex().lstrip('.')
        suffix = '.' + zone
        if not host.endswith(suffix):
            return None
        leaf = host[: -len(suffix)]
        if not leaf or '.' in leaf:                                               # Reject nested subdomains
            return None
        try:
            return Safe_Str__Slug(leaf)
        except Exception:
            return None

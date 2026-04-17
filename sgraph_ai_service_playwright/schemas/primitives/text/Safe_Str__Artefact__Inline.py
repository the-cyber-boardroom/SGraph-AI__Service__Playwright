# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Artefact__Inline primitive
#
# Carries base64-encoded artefact payloads (PNG screenshots, PDFs, HARs) that
# travel inline in Schema__Artefact__Ref.inline_b64 when sink=INLINE. Reuses
# Safe_Str__Text__Dangerous's regex (same allowed alphabet — base64 chars are
# a proper subset of the "dangerous text" alphabet) but bumps max_length from
# 64 KB to 20 MB so a full-page screenshot of a real site (typically 100 KB –
# 2 MB once base64-expanded) fits.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous import Safe_Str__Text__Dangerous


SAFE_STR__ARTEFACT__INLINE__MAX_LENGTH = 20 * 1024 * 1024                            # 20 MB — comfortably above AWS Lambda's 6 MB sync response limit; callers that hit it should be using sink=S3 / sink=LOCAL anyway


class Safe_Str__Artefact__Inline(Safe_Str__Text__Dangerous):
    max_length = SAFE_STR__ARTEFACT__INLINE__MAX_LENGTH

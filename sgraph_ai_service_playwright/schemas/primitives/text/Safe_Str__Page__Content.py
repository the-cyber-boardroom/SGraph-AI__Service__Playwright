# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Page__Content primitive
#
# Carries rendered page HTML / text content returned by GET_CONTENT. Reuses
# Safe_Str__Text__Dangerous's regex (HTML contains the same "dangerous" chars)
# but bumps max_length from 64 KB to 10 MB — real-world pages routinely run
# 100 KB – 5 MB after JS hydration.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous import Safe_Str__Text__Dangerous


SAFE_STR__PAGE__CONTENT__MAX_LENGTH = 10 * 1024 * 1024                                # 10 MB — covers 99%+ of real pages; still under Lambda's 6 MB response cap when used in Quick__Html since response is JSON-encoded and served via the Function URL


class Safe_Str__Page__Content(Safe_Str__Text__Dangerous):
    max_length = SAFE_STR__PAGE__CONTENT__MAX_LENGTH

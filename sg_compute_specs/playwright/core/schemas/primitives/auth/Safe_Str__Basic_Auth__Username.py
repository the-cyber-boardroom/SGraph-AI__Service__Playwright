# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Basic_Auth__Username
#
# Real proxy usernames (mitmproxy --proxyauth, corp HTTP proxies, Oxylabs /
# BrightData session IDs) routinely contain hyphens, dots and underscores —
# osbot_utils' Safe_Str__Username is narrower (alphanumerics + underscore only)
# and silently converts hyphens to underscores, which flips `qa-user` into
# `qa_user` and produces an unexplained 407 against any proxy expecting the
# original form.
#
# This type accepts the character class HTTP basic-auth usernames can legally
# carry without the `:` separator (RFC 7617 does not constrain userid further
# than "no colon"). No length floor — some proxy-tier sessions use 4-char
# identifiers. Max length kept conservative.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str


class Safe_Str__Basic_Auth__Username(Safe_Str):
    regex      = re.compile(r'[^a-zA-Z0-9_\-.]')                                    # Strip anything outside alphanumerics + _ - . — keeps hyphenated usernames intact
    max_length = 128                                                                # Plenty for session-id style creds

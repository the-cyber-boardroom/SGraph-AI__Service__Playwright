# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Url__Permissive primitive (BUG-1 fix)
#
# osbot-utils' Safe_Str__Url excludes ':' (and other RFC 3986 pchar characters)
# from the fragment class, which incorrectly rejects vault-style URLs like
#   https://host/#tcss7to5vfp6asjbm1t1p5ng:rqw3wk4b
# (the colon between vault-id and access-key is legal per RFC 3986
# `fragment = *( pchar / "/" / "?" )`, and pchar includes ":").
#
# This primitive is a drop-in replacement with an RFC-compliant character class
# for path / query / fragment — exactly the same shape (scheme + host + port +
# path? + query? + fragment?), just stops rejecting characters the spec allows.
#
# To upstream into osbot-utils later — see the debrief response pack
# (team/roles/architect/reviews/05/30/playwright-debrief-response/) BUG-1.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


# RFC 3986 pchar = unreserved / pct-encoded / sub-delims / ":" / "@".
# Path     = *( pchar / "/" ).
# Query    = *( pchar / "/" / "?" ).
# Fragment = *( pchar / "/" / "?" ).
_URL__PATH_CHARS  = r"a-zA-Z0-9\-._~%!$&'()*+,;=:@/"                                # pchar + "/"
_URL__QUERY_FRAG  = _URL__PATH_CHARS + r"?"                                          # pchar + "/" + "?"
URL_REGEX = re.compile(
    r'^https?://'                                                                    # scheme
    r'[a-zA-Z0-9.\-]+'                                                               # host
    r'(:[0-9]{1,5})?'                                                                # port
    r'(/[' + _URL__PATH_CHARS + r']*)?'                                              # path
    r'(\?[' + _URL__QUERY_FRAG + r']*)?'                                             # query
    r'(#[' + _URL__QUERY_FRAG + r']*)?'                                              # fragment — the BUG-1 fix
    r'$'
)


class Safe_Str__Url__Permissive(Safe_Str):
    max_length        = 4096                                                         # roomy: vault URLs + share tokens push past the conservative 2048 default
    regex             = URL_REGEX
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True

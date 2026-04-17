# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Proxy__Auth__Basic
#
# Basic-auth credentials for an upstream HTTP(S) proxy. Kept as a *nested*
# schema (not flat fields on Schema__Proxy__Config) to signal that these
# values go through a DIFFERENT mechanism than `server` / `bypass`:
#
#   • server / bypass   → passed to chromium.launch(proxy=...)
#   • username / password → wired via CDP Fetch.authRequired after the page
#                           is created, NOT via launch kwargs (which only
#                           work for a subset of Chromium launch paths and
#                           silently no-op on the modern headless shell)
#
# Future auth types (Bearer, NTLM, etc.) can be added as sibling schemas
# without breaking callers of the basic-auth shape.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                           import Type_Safe

from sgraph_ai_service_playwright.schemas.primitives.auth.Safe_Str__Basic_Auth__Password       import Safe_Str__Basic_Auth__Password
from sgraph_ai_service_playwright.schemas.primitives.auth.Safe_Str__Basic_Auth__Username       import Safe_Str__Basic_Auth__Username


class Schema__Proxy__Auth__Basic(Type_Safe):
    username : Safe_Str__Basic_Auth__Username                                       # Proxy username — hyphens / dots preserved (real proxy creds use them)
    password : Safe_Str__Basic_Auth__Password                                       # Proxy password — never logged, never inspected outside CDP binder

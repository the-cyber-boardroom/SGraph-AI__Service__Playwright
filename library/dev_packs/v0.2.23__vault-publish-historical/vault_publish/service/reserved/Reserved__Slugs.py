# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Reserved__Slugs
# The maintained, versioned reserved-slug and profanity sets. This is a registry
# (module-level constants + a thin helper class), not a schema — the registry
# exception in CLAUDE.md §21. Changes to these sets are policy decisions and are
# treated like changes to the JS expression allowlist.
#
# The profanity set here is illustrative — it carries the *mechanism* (substring
# match), not the policy. The maintained profanity list is supplied out of band.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

RESERVED_SLUGS = frozenset({
    'www'   , 'api'    , 'admin'   , 'docs'    , 'app'    , 'mail'   , 'ftp'   ,
    'smtp'  , 'imap'   , 'pop'     , 'ns'      , 'ns1'    , 'ns2'    , 'dns'   ,
    'mx'    , 'cdn'    , 'assets'  , 'static'  , 'status' , 'help'   , 'support',
    'blog'  , 'shop'   , 'store'   , 'test'    , 'dev'    , 'staging', 'prod'  ,
    'demo'  , 'about'  , 'login'   , 'signup'  , 'signin' , 'logout' , 'account',
    'billing','dashboard','console', 'portal' , 'secure' , 'vpn'    , 'proxy' ,
    'gateway','router' , 'host'    , 'root'    , 'system' , 'internal','public',
    'sgraph', 'send'   , 'vault'   ,
})

PROFANITY_BASIC = frozenset({
    'damn',                                                                  # illustrative only — see header
})


class Reserved__Slugs(Type_Safe):

    def is_reserved(self, raw: str) -> bool:
        return str(raw).lower() in RESERVED_SLUGS

    def is_profane(self, raw: str) -> bool:
        lowered = str(raw).lower()
        return any(bad in lowered for bad in PROFANITY_BASIC)

# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Reserved__Slugs
# Shadow set of slugs that must not be registered. Generous seed per plan Q15
# (decided 2026-05-17). Flat scheme — no namespace tokens.
# ═══════════════════════════════════════════════════════════════════════════════

RESERVED_SLUGS: frozenset = frozenset({
    'www', 'api', 'admin', 'status', 'mail', 'cdn', 'auth',
})

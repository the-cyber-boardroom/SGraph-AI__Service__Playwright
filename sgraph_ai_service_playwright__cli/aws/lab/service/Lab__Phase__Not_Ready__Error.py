# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Phase__Not_Ready__Error
# Raised when an experiment or teardown module requires a phase that hasn't
# shipped yet (e.g. Phase 2 Lambda before v2 vault-publish lands).
# ═══════════════════════════════════════════════════════════════════════════════


class Lab__Phase__Not_Ready__Error(Exception):
    pass

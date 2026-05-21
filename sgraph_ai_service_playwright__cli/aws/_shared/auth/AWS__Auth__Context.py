# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws shared auth: AWS__Auth__Context
# Process-level "which command family is running right now". A guarded command sets its
# family for the duration; the session factory reads it and transparently assumes that
# family's least-privilege role (AWS__Auth__Resolver). Mirrors Sg__Aws__Context's
# module-singleton pattern. Distinct from Sg__Aws__Context.current_role: that is the
# *base* identity (keyring/IMDS) we assume *from*; this is the family we assume *into*.
# ═══════════════════════════════════════════════════════════════════════════════

_active_family : str = ''


def set_active_family(family : str) -> None:
    global _active_family
    _active_family = family or ''


def get_active_family() -> str:
    return _active_family


def clear_active_family() -> None:
    global _active_family
    _active_family = ''

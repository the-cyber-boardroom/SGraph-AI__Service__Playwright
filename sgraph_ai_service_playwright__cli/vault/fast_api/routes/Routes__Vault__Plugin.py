# ═══════════════════════════════════════════════════════════════════════════════
# SHIM — Routes__Vault__Plugin renamed to Routes__Vault__Spec (BV2.9).
# Legacy alias kept for one release. Delete in BV2.12.
# ═══════════════════════════════════════════════════════════════════════════════
from sg_compute.vault.api.routes.Routes__Vault__Spec import Routes__Vault__Spec as Routes__Vault__Plugin  # noqa: F401

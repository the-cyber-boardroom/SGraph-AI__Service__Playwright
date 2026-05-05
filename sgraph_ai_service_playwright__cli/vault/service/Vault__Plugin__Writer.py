# ═══════════════════════════════════════════════════════════════════════════════
# SHIM — Vault__Plugin__Writer renamed to Vault__Spec__Writer (BV2.9).
# Legacy alias kept for one release. Delete in BV2.12.
# ═══════════════════════════════════════════════════════════════════════════════
from sg_compute.vault.service.Vault__Spec__Writer import Vault__Spec__Writer as Vault__Plugin__Writer  # noqa: F401

# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Slug__Routing__Lookup
# Helper for the Waker Lambda — resolves a slug to its registered entry without
# going through the full Vault_Publish__Service. Thin wrapper over Slug__Registry.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Entry import Schema__Vault_Publish__Entry
from sg_compute_specs.vault_publish.service.Slug__Registry                import Slug__Registry


class Slug__Routing__Lookup(Type_Safe):
    _registry_factory: Optional[Callable] = None  # seam: () -> Slug__Registry

    def _registry(self) -> Slug__Registry:
        if self._registry_factory is not None:
            return self._registry_factory()
        return Slug__Registry()

    def lookup(self, slug: str) -> Optional[Schema__Vault_Publish__Entry]:
        return self._registry().get(slug)

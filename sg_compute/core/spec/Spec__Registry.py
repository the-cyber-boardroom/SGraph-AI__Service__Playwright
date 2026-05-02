# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__Registry
# In-memory registry of loaded spec manifests. Populated by Spec__Loader.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                   import Dict, Optional

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.spec.schemas.Schema__Spec__Catalogue                    import Schema__Spec__Catalogue
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry


class Spec__Registry(Type_Safe):
    _specs: Dict[str, Schema__Spec__Manifest__Entry]                         # keyed by spec_id

    def __init__(self):
        self._specs = {}

    def register(self, entry: Schema__Spec__Manifest__Entry) -> None:
        self._specs[entry.spec_id] = entry

    def get(self, spec_id: str) -> Optional[Schema__Spec__Manifest__Entry]:
        return self._specs.get(spec_id)

    def all(self) -> list:
        return list(self._specs.values())

    def spec_ids(self) -> list:
        return list(self._specs.keys())

    def catalogue(self) -> Schema__Spec__Catalogue:
        return Schema__Spec__Catalogue(specs=self.all())

    def __len__(self) -> int:
        return len(self._specs)

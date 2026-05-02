# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__Routes__Loader
# Discovers per-spec route classes by convention from sg_compute_specs.
#
# Convention: for spec_id 'docker' → sg_compute_specs.docker.api.routes.Routes__Docker__Stack
#             for spec_id 'open_design' → sg_compute_specs.open_design.api.routes.Routes__Open_Design__Stack
#
# Specs without a route class are silently skipped (they may only have
# catalogue entries, no HTTP surface yet).
# ═══════════════════════════════════════════════════════════════════════════════

import importlib
from typing                                                                   import List, Tuple, Type

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.spec.Spec__Registry                                     import Spec__Registry


class Spec__Routes__Loader(Type_Safe):
    registry : Spec__Registry

    def load(self) -> List[Tuple[str, Type]]:
        pairs = []
        for spec_id in self.registry.spec_ids():
            routes_cls = self._find_routes_class(spec_id)
            if routes_cls is not None:
                pairs.append((spec_id, routes_cls))
        return pairs

    def _find_routes_class(self, spec_id: str):
        pascal     = self._to_pascal(spec_id)
        class_name = f'Routes__{pascal}__Stack'
        module_fqn = f'sg_compute_specs.{spec_id}.api.routes.{class_name}'
        try:
            module = importlib.import_module(module_fqn)
            return getattr(module, class_name, None)
        except ImportError:
            return None

    @staticmethod
    def _to_pascal(spec_id: str) -> str:
        return ''.join(word.capitalize() for word in spec_id.split('_'))

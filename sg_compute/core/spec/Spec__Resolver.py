# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__Resolver
# Validates the composition DAG across all loaded specs.
# Raises ValueError if any extends list references an unknown spec_id
# or if the graph contains a cycle.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                   import Dict, List, Set

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry


class Spec__Resolver(Type_Safe):

    def validate(self, specs: Dict[str, Schema__Spec__Manifest__Entry]) -> None:
        for spec_id, entry in specs.items():
            for parent_id in entry.extends:
                if parent_id not in specs:
                    raise ValueError(
                        f"spec '{spec_id}' extends unknown spec '{parent_id}'"
                    )
        for spec_id in specs:
            self._detect_cycle(spec_id, specs, set(), [])

    def _detect_cycle(self,
                      current  : str,
                      specs    : Dict[str, Schema__Spec__Manifest__Entry],
                      visiting : Set[str],
                      path     : List[str]) -> None:
        if current in visiting:
            cycle = ' -> '.join(path + [current])
            raise ValueError(f"cycle detected in spec composition graph: {cycle}")
        visiting = visiting | {current}
        path = path + [current]
        entry = specs.get(current)
        if entry is None:
            return
        for parent_id in entry.extends:
            self._detect_cycle(parent_id, specs, visiting, path)

    def topological_order(self,
                          spec_id : str,
                          specs   : Dict[str, Schema__Spec__Manifest__Entry]) -> List[str]:
        """Return spec_ids in topological order (parents before children) for spec_id."""
        result  = []
        visited = set()

        def _visit(sid: str) -> None:
            if sid in visited:
                return
            visited.add(sid)
            entry = specs.get(sid)
            if entry:
                for parent in entry.extends:
                    _visit(parent)
            result.append(sid)

        _visit(spec_id)
        return result

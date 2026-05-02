# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__Loader
# Discovers spec manifests from:
#   1. The sg_compute_specs package (direct walk during incubation period)
#   2. PEP 621 entry points group 'sg_compute.specs' (installed packages)
# Validates the composition graph via Spec__Resolver after loading.
# ═══════════════════════════════════════════════════════════════════════════════

import importlib
import importlib.util
from pathlib                                                                  import Path
from typing                                                                   import List

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.spec.Spec__Registry                                     import Spec__Registry
from sg_compute.core.spec.Spec__Resolver                                     import Spec__Resolver
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry


class Spec__Loader(Type_Safe):

    def load_all(self) -> Spec__Registry:
        registry = Spec__Registry()
        for entry in self._discover():
            registry.register(entry)
        resolver = Spec__Resolver()
        resolver.validate(registry._specs)
        return registry

    def _discover(self) -> List[Schema__Spec__Manifest__Entry]:
        results = []
        results.extend(self._load_from_package())
        results.extend(self._load_from_entry_points())
        return results

    def _load_from_package(self) -> List[Schema__Spec__Manifest__Entry]:
        """Walk sg_compute_specs/ looking for manifest.py files."""
        try:
            import sg_compute_specs as _pkg
        except ImportError:
            return []

        pkg_root = Path(_pkg.__file__).parent
        results  = []
        for manifest_path in sorted(pkg_root.glob('*/manifest.py')):
            spec_id = manifest_path.parent.name
            try:
                module = self._load_manifest_module(manifest_path, spec_id)
                manifest = getattr(module, 'MANIFEST', None)
                if manifest is None:
                    continue
                if not isinstance(manifest, Schema__Spec__Manifest__Entry):
                    raise TypeError(
                        f"manifest.py for spec '{spec_id}' MANIFEST is not "
                        f"Schema__Spec__Manifest__Entry (got {type(manifest).__name__})"
                    )
                results.append(manifest)
            except Exception as e:
                raise RuntimeError(f"failed to load manifest for spec '{spec_id}': {e}") from e
        return results

    def _load_from_entry_points(self) -> List[Schema__Spec__Manifest__Entry]:
        """Load specs advertised via PEP 621 entry points group 'sg_compute.specs'."""
        try:
            from importlib.metadata import entry_points
            group = entry_points(group='sg_compute.specs')
        except Exception:
            return []
        results = []
        for ep in group:
            try:
                module   = ep.load()
                manifest = getattr(module, 'MANIFEST', None)
                if manifest and isinstance(manifest, Schema__Spec__Manifest__Entry):
                    results.append(manifest)
            except Exception:
                pass                                                          # skip broken entry points
        return results

    @staticmethod
    def _load_manifest_module(path: Path, spec_id: str):
        spec = importlib.util.spec_from_file_location(
            f'sg_compute_specs.{spec_id}.manifest', path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__Readme__Resolver
# Resolves the filesystem path to a spec's README.md file.
# When readme_root_override is set (e.g. in tests), uses it as the package root
# instead of importlib package discovery.
# ═══════════════════════════════════════════════════════════════════════════════

import importlib
from pathlib                                                                   import Path
from typing                                                                    import Optional

from osbot_utils.type_safe.Type_Safe                                           import Type_Safe


class Spec__Readme__Resolver(Type_Safe):
    readme_root_override : str = ''                                             # override root for tests

    def readme_path_for_spec(self, spec_id: str) -> Optional[Path]:
        if self.readme_root_override:
            path = Path(self.readme_root_override) / 'sg_compute_specs' / spec_id / 'README.md'
            return path if path.is_file() else None
        try:
            pkg  = importlib.import_module(f'sg_compute_specs.{spec_id}')
            path = Path(pkg.__file__).parent / 'README.md'
            return path if path.is_file() else None
        except ModuleNotFoundError:
            return None

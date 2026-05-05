# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__UI__Resolver
# Resolves the filesystem path to a spec's `ui/` folder.
# When ui_root_override is set (e.g. in tests), uses it as the package root
# instead of importlib package discovery.
# ═══════════════════════════════════════════════════════════════════════════════

import importlib
from pathlib                                                                   import Path
from typing                                                                    import Optional

from osbot_utils.type_safe.Type_Safe                                           import Type_Safe


class Spec__UI__Resolver(Type_Safe):
    ui_root_override : str = ''                                                # override root for tests

    def ui_path_for_spec(self, spec_id: str) -> Optional[Path]:
        if self.ui_root_override:
            path = Path(self.ui_root_override) / 'sg_compute_specs' / spec_id / 'ui'
            return path if path.is_dir() else None
        try:
            pkg  = importlib.import_module(f'sg_compute_specs.{spec_id}')
            path = Path(pkg.__file__).parent / 'ui'
            return path if path.is_dir() else None
        except ModuleNotFoundError:
            return None

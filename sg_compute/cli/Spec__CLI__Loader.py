# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__CLI__Loader
# Discovers per-spec Typer apps from sg_compute_specs/<spec_id>/cli/Cli__<Pascal>.py
# and returns them for mounting under `sg-compute spec <spec_id> <verb>`.
# ═══════════════════════════════════════════════════════════════════════════════

import importlib

from osbot_utils.type_safe.Type_Safe import Type_Safe


def _spec_id_to_pascal(spec_id: str) -> str:
    return ''.join(w.capitalize() for w in spec_id.split('_'))


class Spec__CLI__Loader(Type_Safe):

    def load(self, spec_id: str):
        pascal     = _spec_id_to_pascal(spec_id)
        module_path = f'sg_compute_specs.{spec_id}.cli.Cli__{pascal}'
        try:
            mod = importlib.import_module(module_path)
            return getattr(mod, 'app', None)
        except (ImportError, ModuleNotFoundError):
            return None

    def load_all(self, spec_ids: list) -> dict:
        result = {}
        for spec_id in spec_ids:
            app = self.load(spec_id)
            if app is not None:
                result[spec_id] = app
        return result

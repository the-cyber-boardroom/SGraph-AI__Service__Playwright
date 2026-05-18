# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — experiments registry
# Module-level dict + helpers. Starts empty; agents A–D add entries.
# ═══════════════════════════════════════════════════════════════════════════════

_REGISTRY: dict = {}                                                               # name → Lab__Experiment subclass (not instance)


def register_experiment(name: str, experiment_class) -> None:
    _REGISTRY[name] = experiment_class


def get_experiment(name: str):                                                     # → class | None
    return _REGISTRY.get(name)


def list_experiments() -> list:                                                    # list[dict] one per registered experiment
    result = []
    for name, cls in _REGISTRY.items():
        try:
            meta = cls().metadata()
            result.append({'name': name, 'tier': meta.tier.value, 'phase': meta.phase, 'description': meta.description})
        except Exception:
            result.append({'name': name, 'tier': '', 'phase': '', 'description': ''})
    return result

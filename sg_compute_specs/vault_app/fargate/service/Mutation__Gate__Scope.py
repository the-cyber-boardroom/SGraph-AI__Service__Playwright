# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Mutation__Gate__Scope
# Context manager: when SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS=1, sets all
# per-service mutation gates for the duration then restores original values.
# NOT Type_Safe — requires __enter__/__exit__ protocol (no Type_Safe CM support).
# ═══════════════════════════════════════════════════════════════════════════════

import os


_GATE_ENV = 'SG_VAULT_APP__FARGATE__ALLOW_MUTATIONS'                           # outer gate users export

_INNER_GATES = [                                                                # per-service gates set when outer gate is 1
    'SG_AWS__FARGATE__ALLOW_MUTATIONS',
    'SG_AWS__IAM__ALLOW_MUTATIONS',
    'SG_AWS__ECR__ALLOW_MUTATIONS',
    'SG_AWS__LOGS__ALLOW_MUTATIONS',
]


class Mutation__Gate__Scope:

    def __enter__(self):
        self._saved = {k: os.environ.get(k) for k in _INNER_GATES}             # snapshot current values (None = not set)
        if os.environ.get(_GATE_ENV) == '1':                                   # only unlock if outer gate is set
            for k in _INNER_GATES:
                os.environ[k] = '1'
        return self

    def __exit__(self, *_):
        for k, v in self._saved.items():                                        # restore snapshots (including exception path)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

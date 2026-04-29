# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Neko__Service
# Stub — every operation raises NotImplementedError.
# The plugin manifest ships with enabled=False. A real implementation is gated
# on the experiment results from v0.23.x__neko-evaluation.
#
# See: sgraph_ai_service_playwright__cli/neko/docs/README.md
#      team/humans/dinis_cruz/briefs/04/29/v0.22.19__backend-plugin-architecture/04__neko-experiment.md
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

_EXPERIMENT_DOC = (
    'Neko plugin is enabled=False. See '
    'team/humans/dinis_cruz/briefs/04/29/v0.22.19__backend-plugin-architecture/'
    '04__neko-experiment.md for the evaluation plan that gates this implementation.'
)


class Neko__Service(Type_Safe):

    def setup(self) -> 'Neko__Service':
        return self

    def create_stack(self, *args, **kwargs):
        raise NotImplementedError(_EXPERIMENT_DOC)

    def list_stacks(self, region: str = '') -> list:
        return []

    def delete_stack(self, *args, **kwargs):
        raise NotImplementedError(_EXPERIMENT_DOC)

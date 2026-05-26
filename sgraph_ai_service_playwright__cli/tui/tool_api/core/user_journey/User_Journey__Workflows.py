# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/core/user_journey: User_Journey__Workflows
# Curated grant bundles for the chat cockpit (decision #10: the model never picks
# its own tools — a workflow does). Three tiers of trust over the user-journey API:
#   monitor — read-only (status + flows)
#   operate — + start/stop suites
#   load    — + scale (the cost-bearing knob; the execution center still dry-runs/gates it)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.tool_api.core.user_journey.User_Journey__Tui_Api__Provider import API_SLUG
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Grant   import List__Tui_Api__Grant
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Grant import Schema__Tui_Api__Grant
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Workflow import Schema__Tui_Api__Workflow


def _grants(*capabilities) -> List__Tui_Api__Grant:
    grants = List__Tui_Api__Grant()
    for capability in capabilities:
        grants.append(Schema__Tui_Api__Grant(scope=Schema__Tui_Api__Scope(api=API_SLUG, capability=capability)))
    return grants


def monitor() -> Schema__Tui_Api__Workflow:
    return Schema__Tui_Api__Workflow(name='monitor', description='Read-only: suite status + captured flows.',
                                     grants=_grants('read'))


def operate() -> Schema__Tui_Api__Workflow:
    return Schema__Tui_Api__Workflow(name='operate', description='Start and stop suites (+ monitor).',
                                     grants=_grants('read', 'write'))


def load() -> Schema__Tui_Api__Workflow:
    return Schema__Tui_Api__Workflow(name='load', description='Scale suites for load testing (+ operate). Cost-aware.',
                                     grants=_grants('read', 'write', 'scale'))


WORKFLOWS = {'monitor': monitor, 'operate': operate, 'load': load}

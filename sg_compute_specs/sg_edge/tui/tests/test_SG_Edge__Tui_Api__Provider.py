# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui/tui_api: tests for SG_Edge__Tui_Api__Provider
# Drives the provider THROUGH the execution center against a real Local__Edge__Stack
# in a temp dir (no mocks): manifest/contract, read actions, the mutation gate
# (confirm), preconditions/sequencing, dry-run preview, and the AWS source (can_act
# False → write actions unavailable, request unavailable, no crash). Pure — runs on
# 3.11 (no textual; the tool_api framework + data source are framework-free).
# ═══════════════════════════════════════════════════════════════════════════════

import shutil
import tempfile
from unittest import TestCase

from sg_compute_specs.sg_edge.local.Local__Edge__Stack                          import Local__Edge__Stack
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper                      import SG_Edge__DNS__Helper
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Local_Source             import SG_Edge__TUI__Local_Source
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__AWS_Source               import SG_Edge__TUI__AWS_Source
from sg_compute_specs.sg_edge.tui.tui_api.SG_Edge__Tui_Api__Provider            import SG_Edge__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry          import Tui_Api__Registry
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center  import Tui_Api__Execution_Center
from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory

SLUG    = 'sg-edge.local'
APPROVE = lambda *_: True                                                            # an on_confirm that says yes


def _center(source):
    registry = Tui_Api__Registry().register(SG_Edge__Tui_Api__Provider(source=source))
    return Tui_Api__Execution_Center(registry=registry)


class test_SG_Edge__Tui_Api__Provider(TestCase):

    def setUp(self):
        self.dir    = tempfile.mkdtemp(prefix='sg-edge-toolapi-')
        self.source = SG_Edge__TUI__Local_Source(stack=Local__Edge__Stack(state_dir=self.dir))
        self.center = _center(self.source)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    # ── contract ──────────────────────────────────────────────────────────────────
    def test_manifest(self):
        manifest = SG_Edge__Tui_Api__Provider(source=self.source).manifest()
        assert str(manifest.slug) == SLUG
        names = {str(a.name) for a in manifest.actions}
        assert {'status', 'slugs', 'check', 'request', 'register', 'unregister', 'setup', 'teardown'} <= names

    # ── read + the golden mutate loop (gated) ───────────────────────────────────────
    def test_setup_register_request_loop(self):
        assert self.center.execute(SLUG, 'setup',    {},                  on_confirm=APPROVE).ok is True
        assert self.center.execute(SLUG, 'register', {'slug': 'alice'},   on_confirm=APPROVE).ok is True
        req = self.center.execute(SLUG, 'request', {'slug': 'alice'})                # read-only, no confirm needed
        assert req.ok is True
        assert req.data['result']['status_code'] == 200
        assert 'welcome' in req.data['result']['kind']
        slugs = self.center.execute(SLUG, 'slugs', {})
        assert any(s['slug'] == 'alice' for s in slugs.data['result']['slugs'])

    def test_mutation_gate_blocks_without_confirm(self):
        self.center.execute(SLUG, 'setup', {}, on_confirm=APPROVE)
        denied = self.center.execute(SLUG, 'register', {'slug': 'bob'}, on_confirm=lambda *_: False)
        assert denied.ok is False
        assert 'not confirmed' in denied.error
        assert 'bob' not in {s['slug'] for s in self.center.execute(SLUG, 'slugs', {}).data['result']['slugs']}

    def test_dry_run_previews_without_mutating(self):
        self.center.execute(SLUG, 'setup', {}, on_confirm=APPROVE)
        from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Exec_Mode import Enum__Tui_Api__Exec_Mode
        self.center.mode = Enum__Tui_Api__Exec_Mode.DRY_RUN
        result = self.center.execute(SLUG, 'register', {'slug': 'zoe'})
        assert result.dry_run is True
        assert 'zoe' in str(result.preview)
        self.center.mode = Enum__Tui_Api__Exec_Mode.AUTO
        assert 'zoe' not in {s['slug'] for s in self.center.execute(SLUG, 'slugs', {}).data['result']['slugs']}

    def test_invalid_slug_is_a_clean_error(self):
        self.center.execute(SLUG, 'setup', {}, on_confirm=APPROVE)
        result = self.center.execute(SLUG, 'register', {'slug': ''}, on_confirm=APPROVE)
        assert result.ok is False and 'slug is required' in result.error


class test_SG_Edge__Tui_Api__Provider__AWS(TestCase):

    def setUp(self):
        self.r53    = Route53__AWS__Client__In_Memory()
        self.r53.seed_zone('edge.sg-labs.app')
        source      = SG_Edge__TUI__AWS_Source(dns=SG_Edge__DNS__Helper(route53=self.r53))
        self.center = _center(source)

    def test_read_works_writes_unavailable(self):
        assert self.center.execute(SLUG, 'status', {}).ok is True                    # reads work against the live edge DNS
        available = {str(a.name) for a in self.center.available_actions(SLUG)}
        assert 'status' in available and 'slugs' in available
        assert 'register' not in available                                           # can_act False → write actions invisible
        assert 'request'  not in available                                           # request is local-only too
        blocked = self.center.execute(SLUG, 'register', {'slug': 'x'}, on_confirm=APPROVE)
        assert blocked.ok is False                                                   # precondition refusal — no crash

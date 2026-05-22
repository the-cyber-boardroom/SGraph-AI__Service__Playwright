# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui/tui_api: SG_Edge__Tui_Api__Provider
# The SG/Edge edge as a TUI API — driveable by humans, pytest, the explorer, and the
# Bedrock chat alike (the "talk to your edge" consumer). It owns NO logic: every
# action delegates to the injected SG_Edge__TUI__Data_Source — the SAME backend the
# `sg edge local *` CLI and the Control Center use (separation guide). Read actions
# are READ_ONLY; mutations are WRITE/CRUD/DESTRUCTIVE and the execution center gates
# them (scope + confirm/env). state() drives the preconditions: write actions require
# `can_act` (False on the AWS target → invisible, never a crash). Mirrors the S3
# provider; inject a Local source over a temp stack for no-mock tests.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Change_Kind        import Enum__Tui_Api__Change_Kind
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Cond_Op            import Enum__Tui_Api__Cond_Op
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier               import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Action            import List__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Precondition      import List__Tui_Api__Precondition
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Tier              import List__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action          import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Manifest        import Schema__Tui_Api__Manifest
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Orientation     import Schema__Tui_Api__Orientation
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Precondition    import Schema__Tui_Api__Precondition
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result          import Schema__Tui_Api__Result
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope           import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Skills          import Schema__Tui_Api__Skills
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Change_Log              import Tui_Api__Change_Log
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Provider                import Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Schema__Builder         import Tui_Api__Schema__Builder
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Data_Source                          import SG_Edge__TUI__Data_Source
from sg_compute_specs.sg_edge.tui.tui_api.schemas.Schema__SG_Edge__Tui_Api__Params__Slug     import Schema__SG_Edge__Tui_Api__Params__Slug

SLUG    = 'sg-edge.local'
TOOL    = 'sg-edge'
NO_ARGS = {'type': 'object', 'properties': {}}

READ_ONLY   = Enum__Tui_Api__Tier.READ_ONLY
WRITE       = Enum__Tui_Api__Tier.WRITE
CRUD        = Enum__Tui_Api__Tier.CRUD
DESTRUCTIVE = Enum__Tui_Api__Tier.DESTRUCTIVE


def _scope(capability : str) -> Schema__Tui_Api__Scope:
    return Schema__Tui_Api__Scope(api=SLUG, capability=capability)


def _can_act_precondition() -> List__Tui_Api__Precondition:                          # write actions are unavailable when the source can't act (AWS → pending Slice 5)
    out = List__Tui_Api__Precondition()
    out.append(Schema__Tui_Api__Precondition(state_path='can_act', op=Enum__Tui_Api__Cond_Op.EQ, value='True',
                                             note='mutations are local-only (AWS edge is read-only — pending Slice 5)'))
    return out


class SG_Edge__Tui_Api__Provider(Tui_Api__Provider):
    source  : SG_Edge__TUI__Data_Source                                              # inject a Local source over a temp stack in tests
    builder : Tui_Api__Schema__Builder

    # ── contract ────────────────────────────────────────────────────────────────
    def manifest(self) -> Schema__Tui_Api__Manifest:
        slug_schema = self.builder.input_schema(Schema__SG_Edge__Tui_Api__Params__Slug)
        read        = _scope('read')
        write       = _scope('write')
        admin       = _scope('admin')

        actions = List__Tui_Api__Action()
        actions.append(Schema__Tui_Api__Action(name='status', tier=READ_ONLY, scope=read,
                                               description='Edge snapshot: deployed?, wildcard, fleet IPs, zero_streak, slug count.',
                                               input_schema=NO_ARGS))
        actions.append(Schema__Tui_Api__Action(name='slugs', tier=READ_ONLY, scope=read,
                                               description='List registered slugs with state (live / dormant / orphan) + backend.',
                                               input_schema=NO_ARGS))
        actions.append(Schema__Tui_Api__Action(name='check', tier=READ_ONLY, scope=read,
                                               description='Deviation findings for the edge (orphan backend, dormant slug, missing wildcard/fleet).',
                                               input_schema=NO_ARGS))
        actions.append(Schema__Tui_Api__Action(name='request', tier=READ_ONLY, scope=read,
                                               description='Simulate a user request to a slug → welcome (200) / dormant (503) / not-recognised (404). Read-only.',
                                               input_schema=slug_schema, preconditions=_can_act_precondition()))
        actions.append(Schema__Tui_Api__Action(name='register', tier=WRITE, scope=write, supports_dry_run=True,
                                               description='Register a slug: write its A record + _sg.<slug> backend TXT (a live slug).',
                                               input_schema=slug_schema, preconditions=_can_act_precondition()))
        actions.append(Schema__Tui_Api__Action(name='register_dormant', tier=WRITE, scope=write, supports_dry_run=True,
                                               description='Register a slug A-record only (dormant — no backend; first request wakes the Vault Waker).',
                                               input_schema=slug_schema, preconditions=_can_act_precondition()))
        actions.append(Schema__Tui_Api__Action(name='unregister', tier=CRUD, scope=write, supports_dry_run=True,
                                               description='Remove a slug: delete its A + _sg.<slug> TXT records.',
                                               input_schema=slug_schema, preconditions=_can_act_precondition()))
        actions.append(Schema__Tui_Api__Action(name='setup', tier=WRITE, scope=write, supports_dry_run=True,
                                               description='Bring the local edge up: DNS zone + wildcard + one proxy in the fleet.',
                                               input_schema=NO_ARGS, preconditions=_can_act_precondition()))
        actions.append(Schema__Tui_Api__Action(name='teardown', tier=DESTRUCTIVE, scope=admin, supports_dry_run=True,
                                               description='Destroy the local edge: delete the local DNS + stack state. Confirm required.',
                                               input_schema=NO_ARGS, preconditions=_can_act_precondition()))

        tiers = List__Tui_Api__Tier()
        for tier in (READ_ONLY, WRITE, CRUD, DESTRUCTIVE):
            tiers.append(tier)

        return Schema__Tui_Api__Manifest(slug=SLUG, tool=TOOL, name='SG/Edge (local)', version='0.1.0',
                                        description='Operate the local SG/Edge edge: read state + register / request / setup / teardown slugs.',
                                        tiers=tiers, actions=actions, skills=Schema__Tui_Api__Skills())

    def state(self) -> dict:                                                         # drives preconditions + orientation
        snapshot = self.source.snapshot()
        return {'deployed'   : snapshot.deployed,
                'zone_exists': snapshot.zone_exists,
                'can_act'    : self.source.can_act(),
                'parent'     : snapshot.parent,
                'slug_count' : len(snapshot.slugs)}

    def orientation(self) -> Schema__Tui_Api__Orientation:
        log = Tui_Api__Change_Log()
        log.add(Enum__Tui_Api__Change_Kind.FEATURE,
                'SG/Edge local TUI API: status/slugs/check/request + register/setup/teardown (gated).', '0.1.0')
        snapshot = self.source.snapshot()
        return Schema__Tui_Api__Orientation(tool=TOOL,
                                          status={'healthy': True, 'deployed': bool(snapshot.deployed),
                                                  'parent': str(snapshot.parent), 'can_act': self.source.can_act()},
                                          recent_changes=log.changes)

    def skills(self) -> dict:
        import os
        here = os.path.join(os.path.dirname(__file__), 'skills')
        out  = {}
        for audience, filename in (('human', 'SKILL-human.md'), ('api', 'SKILL-api.md'), ('driver', 'SKILL-driver.md')):
            path = os.path.join(here, filename)
            if os.path.exists(path):
                with open(path, encoding='utf-8') as handle:
                    out[audience] = handle.read()
        return out

    # ── previews + dispatch (delegate to the data source) ──────────────────────────
    def dry_run(self, action: str, params: dict) -> dict:
        slug = (params or {}).get('slug', '')
        return {'register'        : {'writes': f'{slug} A + _sg.{slug} TXT (live)'},
                'register_dormant': {'writes': f'{slug} A only (dormant)'},
                'unregister'      : {'removes': f'{slug} A + _sg.{slug} TXT'},
                'setup'           : {'creates': 'DNS zone + wildcard + 1 proxy'},
                'teardown'        : {'deletes': 'local DNS + stack state'}}.get(action, {})

    def dispatch(self, action: str, params: dict) -> Schema__Tui_Api__Result:
        params = params or {}
        try:
            if   action == 'status':
                data = self.source.snapshot().json()
            elif action == 'slugs':
                data = {'slugs': [slug.json() for slug in self.source.snapshot().slugs]}
            elif action == 'check':
                data = {'issues': [issue.json() for issue in self.source.snapshot().issues]}
            elif action == 'request':
                slug = self._slug(params)
                resp = self.source.request(slug)
                data = {'slug': slug, 'status_code': resp.status_code, 'kind': str(resp.kind),
                        'title': resp.title, 'backend': resp.backend}
            elif action == 'register':
                slug = self._slug(params)
                data = self.source.register(slug).json()
            elif action == 'register_dormant':
                slug = self._slug(params)
                data = self.source.register(slug, with_backend=False).json()
            elif action == 'unregister':
                slug = self._slug(params)
                data = {'slug': slug, 'removed': bool(self.source.unregister(slug))}
            elif action == 'setup':
                data = self.source.setup().json()
            elif action == 'teardown':
                data = {'removed': bool(self.source.teardown())}
            else:
                return Schema__Tui_Api__Result(ok=False, error=f'unknown action: {action}')
        except ValueError as exc:                                                    # e.g. a slug-required guard
            return Schema__Tui_Api__Result(ok=False, error=str(exc))
        except Exception as exc:                                                     # e.g. AWS source raises (pending Slice 5) → honest error, never a crash
            return Schema__Tui_Api__Result(ok=False, error=f'{type(exc).__name__}: {exc}')
        return Schema__Tui_Api__Result(ok=True, data={'result': data})

    def _slug(self, params: dict) -> str:
        slug = str(params.get('slug', '')).strip()
        if not slug:
            raise ValueError('slug is required')
        return slug

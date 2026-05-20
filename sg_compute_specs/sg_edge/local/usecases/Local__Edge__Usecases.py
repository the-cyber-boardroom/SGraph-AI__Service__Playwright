# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Local__Edge__Usecases
# Scripted, individually-runnable end-to-end use-cases over the local edge stack —
# the user/use-case-POV simulation of the platform. Each use-case runs in its own
# isolated temp state dir (it never touches the operator's `sg edge local setup`
# deployment), drives the real Local__Edge__Stack, and records ordered pass/fail
# steps. These mirror the brief's F-01 / X-06 / X-07 flows, locally and in ms.
#
# USECASES is a registry (id → name + handler) — the one logic-not-schema module
# allowed to hold module-level constants + functions (rule #21).
# ═══════════════════════════════════════════════════════════════════════════════

import shutil
import tempfile

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.sg_edge.local.Local__Edge__Stack                              import Local__Edge__Stack
from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Response_Kind          import Enum__Local__Edge__Response_Kind
from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Severity               import Enum__Local__Edge__Severity
from sg_compute_specs.sg_edge.local.usecases.Schema__Local__Edge__Usecase_Result    import Schema__Local__Edge__Usecase_Result
from sg_compute_specs.sg_edge.local.usecases.Schema__Local__Edge__Usecase_Step      import Schema__Local__Edge__Usecase_Step

WELCOME        = Enum__Local__Edge__Response_Kind.WELCOME
DORMANT        = Enum__Local__Edge__Response_Kind.DORMANT
NOT_RECOGNISED = Enum__Local__Edge__Response_Kind.NOT_RECOGNISED


class Local__Edge__Usecases(Type_Safe):

    def list(self) -> list:                                                          # [(id, name, description), ...]
        return [(uc_id, name, desc) for uc_id, (name, desc, _) in USECASES.items()]

    def run(self, uc_id: str) -> Schema__Local__Edge__Usecase_Result:
        uc_id = uc_id.strip().upper()
        if uc_id not in USECASES:
            raise ValueError(f'unknown use-case {uc_id!r} — known: {", ".join(USECASES)}')
        name, _desc, handler = USECASES[uc_id]
        state_dir = tempfile.mkdtemp(prefix='sg-edge-uc-')
        try:
            steps  = handler(Local__Edge__Stack(state_dir=state_dir))
            result = Schema__Local__Edge__Usecase_Result(id=uc_id, name=name, passed=all(s.ok for s in steps))
            for s in steps:
                result.steps.append(s)
            return result
        finally:
            shutil.rmtree(state_dir, ignore_errors=True)

    def run_all(self) -> list:
        return [self.run(uc_id) for uc_id in USECASES]


# ── step helper ─────────────────────────────────────────────────────────────────

def _step(label: str, ok: bool, detail: str = '') -> Schema__Local__Edge__Usecase_Step:
    return Schema__Local__Edge__Usecase_Step(label=label, ok=bool(ok), detail=detail)


# ── use-case bodies ───────────────────────────────────────────────────────────────

def _uc_fresh_setup(stack) -> list:
    st = stack.setup()
    return [
        _step('setup marks edge deployed',  st.deployed,           f'deployed={st.deployed}'),
        _step('wildcard *.<parent> written', st.wildcard,          f'wildcard={st.wildcard}'),
        _step('one proxy in the fleet',      len(st.proxy_ips) == 1, f'proxy_ips={[str(ip) for ip in st.proxy_ips]}'),
    ]


def _uc_register_and_welcome(stack) -> list:
    stack.setup()
    stack.register('alice')
    r = stack.request('alice')
    return [
        _step('request returns 200',         r.status_code == 200,        f'status={r.status_code}'),
        _step('kind is WELCOME',             r.kind == WELCOME,           f'kind={r.kind}'),
        _step('serves the slug welcome page', 'Welcome to the alice vault' in r.body, r.title),
        _step('backend resolved',            bool(r.backend),             f'backend={r.backend}'),
    ]


def _uc_unknown_slug(stack) -> list:
    stack.setup()
    r = stack.request('ghost')
    return [
        _step('request returns 404',         r.status_code == 404,        f'status={r.status_code}'),
        _step('kind is NOT_RECOGNISED',      r.kind == NOT_RECOGNISED,    f'kind={r.kind}'),
        _step('no backend served',           not r.backend,               f'backend={r.backend or "(none)"}'),
    ]


def _uc_dormant_slug(stack) -> list:
    stack.setup()
    stack.register('bob', with_backend=False)
    r = stack.request('bob')
    return [
        _step('request returns 503',         r.status_code == 503,        f'status={r.status_code}'),
        _step('kind is DORMANT',             r.kind == DORMANT,           f'kind={r.kind}'),
        _step('serves the waking-up page',   'waking up' in r.body,       r.title),
    ]


def _uc_unregister(stack) -> list:
    stack.setup()
    stack.register('carol')
    before = stack.request('carol')
    removed = stack.unregister('carol')
    after  = stack.request('carol')
    return [
        _step('welcome before unregister',   before.kind == WELCOME,      f'kind={before.kind}'),
        _step('unregister removed records',  removed,                     f'removed={removed}'),
        _step('not recognised after',        after.kind == NOT_RECOGNISED, f'kind={after.kind}'),
    ]


def _uc_check_clean(stack) -> list:
    stack.setup()
    stack.register('dave')
    chk      = stack.check()
    bad      = [i for i in chk.issues if i.severity in (Enum__Local__Edge__Severity.WARN,
                                                        Enum__Local__Edge__Severity.ERROR)]
    return [
        _step('check finds the slug',        any(s.slug == 'dave' for s in chk.slugs), f'slugs={[s.slug for s in chk.slugs]}'),
        _step('no WARN/ERROR deviations',    len(bad) == 0,               f'deviations={[i.message for i in bad]}'),
    ]


USECASES = {
    'UC-01': ('fresh-setup',          'Bring the edge up from scratch and confirm it is deployed.',        _uc_fresh_setup),
    'UC-02': ('register-and-welcome', 'Register a slug and confirm the welcome page is served end-to-end.', _uc_register_and_welcome),
    'UC-03': ('unknown-slug',         'Request an unregistered slug and confirm the 404 page.',             _uc_unknown_slug),
    'UC-04': ('dormant-slug',         'Register a slug with no backend and confirm the dormant/loading page.', _uc_dormant_slug),
    'UC-05': ('unregister',           'Register, serve, unregister, and confirm the slug stops resolving.', _uc_unregister),
    'UC-06': ('check-clean',          'A freshly set-up edge with one slug reports no deviations.',         _uc_check_clean),
}

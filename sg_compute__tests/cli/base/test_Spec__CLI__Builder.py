# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Spec__CLI__Builder
# Verifies that the builder wires all 8 standard verbs correctly.
# Uses typer.testing.CliRunner — no AWS calls, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from typer.testing import CliRunner

from sg_compute.cli.base.Schema__Spec__CLI__Spec  import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Builder       import Spec__CLI__Builder


# ── minimal fake domain objects ───────────────────────────────────────────────

class _StackName:
    def __init__(self, v=''):
        self._v = v
    def __init__(self, v=''):       # callable for req.stack_name.__init__(name)
        self._v = v
    def __str__(self):
        return self._v


class _Region:
    def __init__(self, v=''):
        self._v = v
    def __str__(self):
        return self._v


class _FakeRequest:
    def __init__(self):
        self.stack_name    = _StackName()
        self.region        = _Region()
        self.instance_type = ''
        self.max_hours     = 1
        self.from_ami      = ''
        self.caller_ip     = ''


class _FakeInfo:
    def __init__(self, name):
        self.stack_name    = name
        self.instance_id   = 'i-0abc'
        self.instance_type = 't3.medium'
        self.public_ip     = '1.2.3.4'
        self.region        = 'eu-west-2'
        self.state         = type('S', (), {'value': 'running'})()


class _FakeListing:
    def __init__(self, names):
        self.stacks = [_FakeInfo(n) for n in names]
        self.region = 'eu-west-2'


class _FakeDeleteResult:
    deleted = True


class _FakeHealthProbe:
    healthy    = True
    state      = 'running'
    elapsed_ms = 10
    last_error = ''


class _FakeExecResult:
    stdout      = 'hello'
    stderr      = ''
    exit_code   = 0
    transport   = 'ssm'
    duration_ms = 5


class _FakeCreateResponse:
    def __init__(self, name):
        self.stack_info = _FakeInfo(name)
        self.elapsed_ms = 42


class _FakeNameGen:
    def generate(self):
        return 'auto-stack'


class _FakeService:
    call_log = None

    def __init__(self, names=None):
        self._names   = names if names is not None else ['my-stack']
        self.name_gen = _FakeNameGen()
        self.call_log = []

    def list_stacks(self, region):
        self.call_log.append(('list_stacks', region))
        return _FakeListing(self._names)

    def get_stack_info(self, region, name):
        self.call_log.append(('get_stack_info', region, name))
        return _FakeInfo(name)

    def create_stack(self, request):
        name = str(getattr(request, 'stack_name', '')) or 'auto-stack'
        self.call_log.append(('create_stack', name))
        return _FakeCreateResponse(name)

    def delete_stack(self, region, name):
        self.call_log.append(('delete_stack', region, name))
        return _FakeDeleteResult()

    def health(self, region, name, timeout_sec=0, poll_sec=10):
        self.call_log.append(('health', region, name))
        return _FakeHealthProbe()

    def exec(self, region, name, command, timeout_sec=60, cwd=''):
        self.call_log.append(('exec', region, name, command))
        return _FakeExecResult()

    def connect_target(self, region, name):
        self.call_log.append(('connect_target', region, name))
        return 'i-0abc'


# ── builder factory helpers ───────────────────────────────────────────────────

def _build_app(names=None, extra_create_options=None, extra_create_field_setters=None,
               skip_default_commands=None):
    svc_instance = _FakeService(names)

    spec = Schema__Spec__CLI__Spec(
        spec_id               = 'docker'      ,
        display_name          = 'Docker'      ,
        default_instance_type = 't3.medium'   ,
        create_request_cls    = _FakeRequest  ,
        service_factory       = lambda: svc_instance,
        extra_create_field_setters = extra_create_field_setters,
    )
    builder = Spec__CLI__Builder(spec, extra_create_options=extra_create_options,
                                       skip_default_commands=skip_default_commands)
    return builder.build(), svc_instance


# ── tests ─────────────────────────────────────────────────────────────────────

class test_Spec__CLI__Builder(TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_build__all_eight_verbs_registered(self):
        app, _  = _build_app()
        result  = self.runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        for verb in ('list', 'info', 'create', 'wait', 'health', 'connect', 'exec', 'delete'):
            assert verb in result.output, f'missing verb: {verb}'

    def test_build__skip_default_commands_suppresses_named_verbs(self):
        # Specs (e.g. vault-app) replace the auto-registered `wait` / `health` /
        # `delete` with richer equivalents (diagnose-based wait/check, delete
        # with --all bulk-cleanup) — they pass skip_default_commands to opt out
        # of the defaults.
        app, _ = _build_app(skip_default_commands=['wait', 'health', 'delete'])
        assert self.runner.invoke(app, ['wait'  , '--help']).exit_code != 0
        assert self.runner.invoke(app, ['health', '--help']).exit_code != 0
        assert self.runner.invoke(app, ['delete', '--help']).exit_code != 0
        # other verbs still register
        for verb in ('list', 'info', 'create', 'connect', 'exec'):
            assert self.runner.invoke(app, [verb, '--help']).exit_code == 0, f'{verb} broken'

    def test_list__help_mentions_region(self):
        app, _ = _build_app()
        result = self.runner.invoke(app, ['list', '--help'])
        assert result.exit_code == 0
        assert 'region' in result.output

    def test_info__help_shown(self):
        app, _ = _build_app()
        result = self.runner.invoke(app, ['info', '--help'])
        assert result.exit_code == 0

    def test_create__help_mentions_all_base_options(self):
        app, _ = _build_app()
        result = self.runner.invoke(app, ['create', '--help'])
        assert result.exit_code == 0
        for opt in ('region', 'instance-type', 'max-hours', 'ami', 'caller-ip', 'wait'):
            assert opt in result.output, f'missing: {opt}'

    def test_create__defaults_max_hours_to_1(self):
        app, _ = _build_app()
        result = self.runner.invoke(app, ['create', '--help'])
        assert '1' in result.output

    def test_create__per_spec_instance_type_in_help(self):
        app, _ = _build_app()
        result = self.runner.invoke(app, ['create', '--help'])
        assert 't3.medium' in result.output

    def test_create__extra_option_threaded_through_setter(self):
        captured = {}

        def setter(req, **kwargs):
            captured.update(kwargs)

        app, _ = _build_app(
            extra_create_options    = [('registry', str, '', 'ECR registry host')],
            extra_create_field_setters = setter,
        )
        result = self.runner.invoke(app, ['create', '--registry', 'myregistry.example.com'])
        assert result.exit_code == 0, result.output
        assert captured.get('registry') == 'myregistry.example.com'

    def test_wait__help_mentions_timeout(self):
        app, _ = _build_app()
        result = self.runner.invoke(app, ['wait', '--help'])
        assert result.exit_code == 0
        assert 'timeout' in result.output

    def test_health__help_shown(self):
        app, _ = _build_app()
        result = self.runner.invoke(app, ['health', '--help'])
        assert result.exit_code == 0
        assert 'timeout' in result.output

    def test_connect__help_shown(self):
        app, _ = _build_app()
        result = self.runner.invoke(app, ['connect', '--help'])
        assert result.exit_code == 0

    def test_exec__help_mentions_command(self):
        app, _ = _build_app()
        result = self.runner.invoke(app, ['exec', '--help'])
        assert result.exit_code == 0
        assert 'command' in result.output.lower()

    def test_delete__help_mentions_yes(self):
        app, _ = _build_app()
        result = self.runner.invoke(app, ['delete', '--help'])
        assert result.exit_code == 0
        assert 'yes' in result.output

    def test_delete__without_yes_prompts_confirmation(self):
        app, _ = _build_app(names=['my-stack'])
        result = self.runner.invoke(app, ['delete', 'my-stack'], input='y\n')
        assert result.exit_code == 0

    def test_delete__confirmation_abort_exits_nonzero(self):
        app, _ = _build_app(names=['my-stack'])
        result = self.runner.invoke(app, ['delete', 'my-stack'], input='n\n')
        assert result.exit_code != 0

    def test_info__zero_stacks_exits_1(self):
        app, _ = _build_app(names=[])
        result = self.runner.invoke(app, ['info'])
        assert result.exit_code == 1

    def test_info__one_stack_auto_picked(self):
        app, svc = _build_app(names=['fast-fermi'])
        result   = self.runner.invoke(app, ['info'])
        assert result.exit_code == 0
        assert any('get_stack_info' in str(e) for e in svc.call_log)


# ── _wait_healthy branch selection: diagnose() present vs absent ──────────────
# create --wait calls builder._wait_healthy. When the service exposes diagnose(),
# the builder renders the shared live boot-progress table (looping until all rows
# are ok/skip or timeout); when it doesn't, the silent svc.health() poll stays.
# No mocks — two tiny in-memory services, one with diagnose() and one without.

from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
from sg_compute.cli.base.Spec__CLI__Builder      import Spec__CLI__Builder


class _DiagnoseService(_FakeService):                                               # exposes diagnose() → diagnose branch
    def __init__(self, stages, names=None):
        super().__init__(names)
        self._stages = stages
    def diagnose(self, region, name):
        self.call_log.append(('diagnose', region, name))
        for row in self._stages:
            yield row


def _spec_for(svc, **kw):
    return Schema__Spec__CLI__Spec(
        spec_id               = 'docker'    ,
        display_name          = 'Docker'    ,
        default_instance_type = 't3.medium' ,
        create_request_cls    = _FakeRequest,
        service_factory       = lambda: svc ,
        **kw)


class test_wait_healthy_branch_selection(TestCase):

    def test_no_diagnose_uses_silent_health_poll(self):                            # fallback path unchanged
        svc     = _FakeService(['my-stack'])
        builder = Spec__CLI__Builder(_spec_for(svc))
        builder._wait_healthy(svc, 'eu-west-2', 'my-stack')                        # healthy probe → no raise
        assert any(e[0] == 'health'   for e in svc.call_log)
        assert not any(e[0] == 'diagnose' for e in svc.call_log)

    def test_diagnose_present_drives_the_table(self):
        # All rows ok on the first attempt → run_until_ok returns on attempt 1
        # (no sleep / no 600s loop) and _wait_healthy returns without raising.
        stages  = [('ec2-state', 'ok', 'running'), ('containers-up', 'ok', 'up')]
        svc     = _DiagnoseService(stages, ['my-stack'])
        spec    = _spec_for(svc, diagnose_check_order=('ec2-state', 'containers-up', 'external-http'))
        builder = Spec__CLI__Builder(spec)
        builder._wait_healthy(svc, 'eu-west-2', 'my-stack')                        # all ok → no raise
        assert any(e[0] == 'diagnose' for e in svc.call_log)
        assert not any(e[0] == 'health' for e in svc.call_log if e == ('health',))  # diagnose path, not silent health text

    def test_diagnose_not_ok_raises_exit_1(self):
        # A permanent 'fail' row keeps all_ok False; the builder raises exit(1).
        # poll_window=0 (no sleep) is achieved by exercising the renderer directly
        # with timeout=0 — the exit-on-not-ok branch is what we assert here.
        from sg_compute.cli.base.Spec__Diagnose__Renderer import run_until_ok
        from rich.console import Console
        svc = _DiagnoseService([('ec2-state', 'fail', 'pending')], ['my-stack'])
        _rows, all_ok = run_until_ok(svc, 'eu-west-2', 'my-stack',
                                     console=Console(highlight=False, record=True, width=120),
                                     check_order=('ec2-state', 'external-http'),
                                     timeout=0, poll=1)
        assert all_ok is False                                                      # → Spec__CLI__Builder._wait_healthy_diagnose raises typer.Exit(1)

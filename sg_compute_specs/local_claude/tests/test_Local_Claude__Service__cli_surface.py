# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Local_Claude__Service CLI surface
# Verifies cli_spec() shape and user-data render structure (no AWS calls).
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.local_claude.service.Local_Claude__Service              import Local_Claude__Service
from sg_compute_specs.local_claude.service.Local_Claude__User_Data__Builder   import Local_Claude__User_Data__Builder


class TestLocalClaudeServiceCliSurface:

    def test_cli_spec_shape(self):
        spec = Local_Claude__Service().cli_spec()
        assert spec.spec_id               == 'local-claude'
        assert spec.display_name          == 'Local Claude'
        assert spec.default_instance_type == 'g5.xlarge'
        assert spec.health_path           == '/v1/models'
        assert spec.health_port           == 8000
        assert spec.health_scheme         == 'http'
        assert spec.create_request_cls.__name__ == 'Schema__Local_Claude__Create__Request'

    def test_user_data_shutdown_before_dnf(self):
        builder    = Local_Claude__User_Data__Builder()
        user_data  = builder.render(stack_name='test-stack', region='eu-west-2', max_hours=1)
        lines      = user_data.splitlines()
        timer_i    = next(i for i, l in enumerate(lines) if 'systemd-run' in l)
        dnf_i      = next(i for i, l in enumerate(lines) if l.strip().startswith('dnf install'))
        assert timer_i < dnf_i, 'auto-terminate timer must appear before any dnf install (L9)'

    def test_user_data_contains_key_sections(self):
        builder   = Local_Claude__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2')
        assert 'nvidia-container-toolkit' in user_data
        assert 'vllm-claude-code'         in user_data
        assert '/v1/models'               in user_data
        assert 'claude-session-venv'      in user_data
        assert 'claude-code-firstboot'    in user_data

    def test_user_data_with_claude_code_false(self):
        builder   = Local_Claude__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2', with_claude_code=False)
        assert 'claude-code-firstboot' not in user_data
        assert 'local-llm-claude.sh'   not in user_data

    def test_user_data_with_sgit_false(self):
        builder   = Local_Claude__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2', with_sgit=False)
        assert 'claude-session-venv' not in user_data

    def test_user_data_model_name_in_vllm_section(self):
        model     = 'org/my-custom-model'
        builder   = Local_Claude__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2', model=model)
        assert model in user_data

    def test_user_data_served_model_name_in_launcher(self):
        builder   = Local_Claude__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2',
                                   served_model_name='my-alias', with_claude_code=True)
        assert 'ANTHROPIC_MODEL="my-alias"' in user_data

    def test_user_data_no_shutdown_when_max_hours_zero(self):
        builder   = Local_Claude__User_Data__Builder()
        user_data = builder.render(stack_name='test-stack', region='eu-west-2', max_hours=0)
        assert 'systemd-run' not in user_data

    def test_diagnose_returns_eight_checks(self, monkeypatch):
        svc = Local_Claude__Service()
        monkeypatch.setattr(svc, 'get_stack_info',
                            lambda region, name: type('I', (), {'state': 'running', 'instance_id': 'i-fake'})())
        def fake_exec(region, name, cmd, timeout_sec=60, cwd=''):
            return type('R', (), {'stdout': 'ok'})()
        monkeypatch.setattr(svc, 'exec', fake_exec)
        # diagnose() is now a generator; filter out the 'checking' sentinel yields
        checks = [(n, s, d) for n, s, d in svc.diagnose('eu-west-2', 'test-stack') if s != 'checking']
        assert len(checks) == 8
        names = [c[0] for c in checks]
        assert names == ['ec2-state', 'ssm-reachable', 'boot-failed', 'boot-ok',
                         'docker', 'gpu', 'vllm-container', 'vllm-api']

    def test_diagnose_stops_at_ec2_not_running(self, monkeypatch):
        svc = Local_Claude__Service()
        monkeypatch.setattr(svc, 'get_stack_info',
                            lambda region, name: type('I', (), {'state': 'pending', 'instance_id': 'i-fake'})())
        checks = [(n, s, d) for n, s, d in svc.diagnose('eu-west-2', 'test-stack') if s != 'checking']
        assert checks[0] == ('ec2-state', 'fail', 'pending')
        assert all(s == 'skip' for _, s, _ in checks[1:])

    def test_diagnose_marks_boot_failed(self, monkeypatch):
        svc = Local_Claude__Service()
        monkeypatch.setattr(svc, 'get_stack_info',
                            lambda region, name: type('I', (), {'state': 'running', 'instance_id': 'i-fake'})())
        def fake_exec(region, name, cmd, timeout_sec=60, cwd=''):
            if 'sg-compute-boot-failed' in cmd:
                return type('R', (), {'stdout': 'YES'})()
            return type('R', (), {'stdout': 'ok'})()
        monkeypatch.setattr(svc, 'exec', fake_exec)
        checks = [(n, s, d) for n, s, d in svc.diagnose('eu-west-2', 'test-stack') if s != 'checking']
        boot_failed = next(c for c in checks if c[0] == 'boot-failed')
        assert boot_failed[1] == 'fail'

# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Ollama__Service CLI surface
# Verifies cli_spec(), pull_model(), claude_session() — the methods the
# Spec__CLI__Builder relies on. Uses a recording stub for self.exec.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.ollama.schemas.Schema__Ollama__Create__Request import Schema__Ollama__Create__Request
from sg_compute_specs.ollama.service.Ollama__Service                  import Ollama__Service


class _RecordingService(Ollama__Service):
    exec_call = None

    def exec(self, region, name, command, timeout_sec=60, cwd=''):
        self.exec_call = (region, name, command, timeout_sec, cwd)
        class _Result:
            stdout      = command
            stderr      = ''
            exit_code   = 0
            transport   = 'ssm'
            duration_ms = 1
        return _Result()

    def get_stack_info(self, region, name):
        class _Info:
            instance_id = 'i-0fakeollama'
        return _Info()


class test_Ollama__Service__cli_surface(TestCase):

    def test_cli_spec__returns_g5_xlarge_default(self):
        spec = Ollama__Service().cli_spec()
        assert spec.spec_id               == 'ollama'
        assert spec.default_instance_type == 'g5.xlarge'

    def test_cli_spec__health_path_is_api_tags(self):
        spec = Ollama__Service().cli_spec()
        assert spec.health_path == '/api/tags'
        assert spec.health_port == 11434

    def test_cli_spec__create_request_cls_is_schema_ollama_create_request(self):
        spec = Ollama__Service().cli_spec()
        assert spec.create_request_cls is Schema__Ollama__Create__Request

    def test_pull_model__delegates_to_exec_with_long_timeout(self):
        svc    = _RecordingService()
        result = svc.pull_model('eu-west-2', 'fast-fermi', 'gpt-oss:20b')
        region, name, command, timeout_sec, _ = svc.exec_call
        assert region            == 'eu-west-2'
        assert name              == 'fast-fermi'
        assert 'ollama pull gpt-oss:20b' in command
        assert timeout_sec       >= 900
        assert result.stdout     == 'ollama pull gpt-oss:20b'

    def test_claude_session__returns_instance_id_via_connect_target(self):
        svc = _RecordingService()
        assert svc.claude_session('eu-west-2', 'fast-fermi') == 'i-0fakeollama'

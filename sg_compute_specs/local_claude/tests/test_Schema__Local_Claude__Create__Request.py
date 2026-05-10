# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Schema__Local_Claude__Create__Request
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.local_claude.enums.Enum__Local_Claude__AMI__Base            import Enum__Local_Claude__AMI__Base
from sg_compute_specs.local_claude.schemas.Schema__Local_Claude__Create__Request  import Schema__Local_Claude__Create__Request


class TestSchemaLocalClaudeCreateRequest:

    def test_defaults(self):
        req = Schema__Local_Claude__Create__Request()
        assert req.region                 == 'eu-west-2'
        assert req.instance_type          == 'g5.xlarge'
        assert req.model                  == 'QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ'
        assert req.served_model_name      == 'local-coder'
        assert req.tool_parser            == 'qwen3_coder'
        assert req.max_model_len          == 65536
        assert req.kv_cache_dtype         == 'fp8'
        assert req.gpu_memory_utilization == 0.92
        assert int(req.disk_size_gb)      == 200
        assert req.ami_base               == Enum__Local_Claude__AMI__Base.AL2023
        assert req.with_claude_code       is True
        assert req.with_sgit              is True
        assert req.use_spot               is True
        assert req.gpu_required           is True
        assert req.max_hours              == 1

    def test_override_model(self):
        req = Schema__Local_Claude__Create__Request()
        req.model = 'another-org/another-model'
        assert req.model == 'another-org/another-model'

    def test_override_use_spot_false(self):
        req = Schema__Local_Claude__Create__Request()
        req.use_spot = False
        assert req.use_spot is False

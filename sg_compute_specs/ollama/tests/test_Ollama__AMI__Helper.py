# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Ollama__AMI__Helper
# Verifies Enum dispatch. Live SSM hits live in tests/deploy/ (gated on AWS creds).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.ollama.enums.Enum__Ollama__AMI__Base import Enum__Ollama__AMI__Base
from sg_compute_specs.ollama.service.Ollama__AMI__Helper   import Ollama__AMI__Helper


class _RecordingHelper(Ollama__AMI__Helper):
    calls = None

    def __init__(self):
        super().__init__()
        self.calls = []

    def latest_dlami_oss_pytorch_26(self, region):
        self.calls.append(('dlami', region))
        return 'ami-dlami-fake'

    def latest_al2023(self, region):
        self.calls.append(('al2023', region))
        return 'ami-al2023-fake'


class test_Ollama__AMI__Helper(TestCase):

    def test_resolve_for_base__dlami_calls_dlami_resolver(self):
        helper = _RecordingHelper()
        ami_id = helper.resolve_for_base('eu-west-2', Enum__Ollama__AMI__Base.DLAMI)
        assert ami_id == 'ami-dlami-fake'
        assert helper.calls == [('dlami', 'eu-west-2')]

    def test_resolve_for_base__al2023_calls_al2023_resolver(self):
        helper = _RecordingHelper()
        ami_id = helper.resolve_for_base('us-east-1', Enum__Ollama__AMI__Base.AL2023)
        assert ami_id == 'ami-al2023-fake'
        assert helper.calls == [('al2023', 'us-east-1')]

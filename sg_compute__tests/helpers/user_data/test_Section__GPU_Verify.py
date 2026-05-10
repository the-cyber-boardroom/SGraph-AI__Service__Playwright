# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Section__GPU_Verify
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.platforms.ec2.user_data.Section__GPU_Verify import Section__GPU_Verify


class test_Section__GPU_Verify(TestCase):

    def setUp(self):
        self.section = Section__GPU_Verify()

    def test_render__contains_nvidia_smi(self):
        out = self.section.render(gpu_required=True)
        assert 'nvidia-smi' in out

    def test_render__exits_47_on_failure(self):
        out = self.section.render(gpu_required=True)
        assert 'exit 47' in out

    def test_render__empty_when_gpu_not_required(self):
        assert self.section.render(gpu_required=False) == ''

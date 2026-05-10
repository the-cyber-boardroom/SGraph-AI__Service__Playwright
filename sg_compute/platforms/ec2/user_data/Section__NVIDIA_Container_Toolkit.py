# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__NVIDIA_Container_Toolkit
# Installs the NVIDIA Container Toolkit on Amazon Linux 2023 so Docker can pass
# GPU devices into containers. Required for vLLM and any other GPU-in-Docker
# workflow. Must run AFTER Section__Docker and BEFORE any docker run with --gpus.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = '''\
# ── NVIDIA Container Toolkit ─────────────────────────────────────────────────
echo '[sg-compute] installing NVIDIA Container Toolkit...'
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo \
  | tee /etc/yum.repos.d/nvidia-container-toolkit.repo
dnf install -y nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker
echo '[sg-compute] NVIDIA Container Toolkit ready'
'''


class Section__NVIDIA_Container_Toolkit(Type_Safe):

    def render(self) -> str:
        return TEMPLATE

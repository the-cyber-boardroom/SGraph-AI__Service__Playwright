# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Ollama__User_Data__Builder
# Assembles the cloud-init bash script for an Ollama EC2 instance.
# Section order: Base → [NVIDIA drivers] → Ollama install → [Pull model] → Shutdown
# No nginx — port 11434 is restricted to allowed_cidr at the SG level.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.helpers.user_data.Section__Base     import Section__Base
from sg_compute.helpers.user_data.Section__Shutdown import Section__Shutdown

NVIDIA_DRIVERS = """
# ── NVIDIA drivers ────────────────────────────────────────────────────────────
echo "[ollama] installing NVIDIA drivers..."
dnf install -y kernel-devel kernel-headers
dnf config-manager --add-repo \\
  https://developer.download.nvidia.com/compute/cuda/repos/amzn2023/x86_64/cuda-amzn2023.repo
dnf install -y cuda-toolkit-12-4 nvidia-driver
modprobe nvidia || true
echo "[ollama] NVIDIA drivers installed"
"""

OLLAMA_INSTALL = """
# ── Ollama install ────────────────────────────────────────────────────────────
echo "[ollama] installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
systemctl enable --now ollama
echo "[ollama] waiting for Ollama to be ready..."
until curl -sf http://localhost:11434/api/tags > /dev/null; do sleep 2; done
echo "[ollama] Ollama is ready"
"""

OLLAMA_PULL = """
# ── Pull model ────────────────────────────────────────────────────────────────
echo "[ollama] pulling model {model_name}..."
ollama pull {model_name}
echo "[ollama] model {model_name} ready"
"""

FOOTER = '\necho "[ephemeral-ec2] ollama boot complete at $(date -u +%FT%TZ)"\n'


class Ollama__User_Data__Builder(Type_Safe):

    def render(self, stack_name  : str  ,
                     region      : str  ,
                     model_name  : str  = 'qwen2.5-coder:7b',
                     gpu_required: bool = True               ,
                     pull_on_boot: bool = True               ,
                     max_hours   : int  = 4                  ) -> str:
        parts = []
        parts.append(Section__Base().render(stack_name=stack_name))

        if gpu_required:
            parts.append(NVIDIA_DRIVERS)

        parts.append(OLLAMA_INSTALL)

        if pull_on_boot:
            parts.append(OLLAMA_PULL.format(model_name=model_name))

        if max_hours > 0:
            parts.append(Section__Shutdown().render(max_hours=max_hours))

        parts.append(FOOTER)
        return '\n'.join(parts)

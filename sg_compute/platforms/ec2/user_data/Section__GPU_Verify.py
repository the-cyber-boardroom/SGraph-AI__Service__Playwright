# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Section__GPU_Verify
# Bash fragment that asserts the instance has a working NVIDIA GPU. Boots fail
# fast with exit 47 when nvidia-smi is unavailable — better than a half-booted
# Ollama on a CPU-only host.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

TEMPLATE = '''\
# ── GPU verification ─────────────────────────────────────────────────────────
echo '[sg-compute] verifying GPU presence...'
nvidia-smi || { echo '[sg-compute] no GPU detected; aborting boot'; exit 47; }
'''


class Section__GPU_Verify(Type_Safe):

    def render(self, gpu_required: bool = True) -> str:
        if not gpu_required:
            return ''
        return TEMPLATE

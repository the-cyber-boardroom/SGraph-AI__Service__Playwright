# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Ollama: Enum__Ollama__AMI__Base
# Which base AMI to launch from. DLAMI ships NVIDIA drivers + CUDA + PyTorch.
# AL2023 is the bare-metal fallback for builds that pre-bake their own.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Ollama__AMI__Base(Enum):
    DLAMI   = 'dlami'
    AL2023  = 'al2023'

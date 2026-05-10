# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Ollama__Create__Request
# Inputs for `sg-compute spec ollama create`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.primitives.Safe_Int__Disk__GB             import Safe_Int__Disk__GB
from sg_compute.primitives.Safe_Str__Ollama__Model        import Safe_Str__Ollama__Model
from sg_compute_specs.ollama.enums.Enum__Ollama__AMI__Base import Enum__Ollama__AMI__Base


class Schema__Ollama__Create__Request(Type_Safe):
    region          : str                       = 'eu-west-2'
    instance_type   : str                       = 'g5.xlarge'    # R4 — gpt-oss:20b needs ≥24 GiB VRAM
    from_ami        : str                       = ''             # explicit AMI ID; overrides ami_base
    stack_name      : str                       = ''             # empty = auto-generate
    caller_ip       : str                       = ''             # empty = auto-detect
    max_hours       : int                       = 1              # D2 — 1h default for every spec
    model_name      : Safe_Str__Ollama__Model   = Safe_Str__Ollama__Model('gpt-oss:20b')
    ami_base        : Enum__Ollama__AMI__Base   = Enum__Ollama__AMI__Base.DLAMI
    disk_size_gb    : Safe_Int__Disk__GB   = Safe_Int__Disk__GB(250)  # 250 GiB default; 0 = keep AMI default
    with_claude     : bool                      = False          # boot Claude integration under tmux
    expose_api      : bool                      = False          # bind 0.0.0.0:11434 (requires SG lockdown)
    allowed_cidr    : str                       = ''             # empty = caller /32; CIDR for port 11434
    pull_on_boot    : bool                      = True           # False = model pre-baked in AMI
    gpu_required    : bool                      = True           # False = allow CPU-only instance types

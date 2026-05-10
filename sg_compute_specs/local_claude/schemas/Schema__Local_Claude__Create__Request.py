# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Local_Claude__Create__Request
# Inputs for `sg local-claude create`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.primitives.Safe_Int__Disk__GB                                     import Safe_Int__Disk__GB
from sg_compute_specs.local_claude.enums.Enum__Local_Claude__AMI__Base import Enum__Local_Claude__AMI__Base


class Schema__Local_Claude__Create__Request(Type_Safe):
    region                : str                            = 'eu-west-2'
    instance_type         : str                            = 'g5.xlarge'
    from_ami              : str                            = ''             # explicit AMI ID; overrides ami_base
    stack_name            : str                            = ''             # empty = auto-generate
    caller_ip             : str                            = ''             # empty = auto-detect
    max_hours             : float                          = 1.0            # D2 — supports fractional hours: 0.1 = 6 min
    model                 : str                            = 'QuantTrio/Qwen3-Coder-30B-A3B-Instruct-AWQ'
    served_model_name     : str                            = 'local-coder'  # alias vLLM serves; must match env vars
    tool_parser           : str                            = 'qwen3_coder'  # verified-working parser for this model
    max_model_len         : int                            = 65536          # requires kv_cache_dtype='fp8' on A10G
    kv_cache_dtype        : str                            = 'fp8'          # mandatory for 65k context on 23 GiB
    gpu_memory_utilization: float                          = 0.92           # ~1.8 GiB head-room for non-cache buffers
    disk_size_gb          : Safe_Int__Disk__GB             = Safe_Int__Disk__GB(200)
    ami_base              : Enum__Local_Claude__AMI__Base  = Enum__Local_Claude__AMI__Base.DLAMI
    with_claude_code      : bool                           = True           # install Claude Code on first boot
    with_sgit             : bool                           = True           # python3.12 venv with sgit
    use_spot              : bool                           = True           # spot by default (~70% cheaper)
    gpu_required          : bool                           = True           # False = allow CPU instances (not recommended)

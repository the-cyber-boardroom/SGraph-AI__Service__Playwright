# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Ollama__Create__Request
# Inputs for `ec2 ollama create`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Ollama__Create__Request(Type_Safe):
    region          : str  = 'eu-west-2'
    instance_type   : str  = 'g4dn.xlarge'    # GPU default; set c7i.4xlarge for CPU-only
    from_ami        : str  = ''               # empty = resolve latest AL2023
    stack_name      : str  = ''               # empty = auto-generate
    caller_ip       : str  = ''               # empty = auto-detect
    max_hours       : int  = 4
    model_name      : str  = 'qwen2.5-coder:7b'
    allowed_cidr    : str  = ''               # empty = caller /32; CIDR for port 11434
    pull_on_boot    : bool = True             # False = model pre-baked in AMI
    gpu_required    : bool = True             # False = allow CPU-only instance types

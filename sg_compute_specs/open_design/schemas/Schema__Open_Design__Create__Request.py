# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Open_Design__Create__Request
# Inputs for `ec2 open-design create`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Open_Design__Create__Request(Type_Safe):
    region          : str  = 'eu-west-2'
    instance_type   : str  = 't3.large'
    from_ami        : str  = ''             # empty = resolve latest AL2023
    stack_name      : str  = ''             # empty = auto-generate
    caller_ip       : str  = ''             # empty = auto-detect
    max_hours       : int  = 1
    api_key         : str  = ''             # ANTHROPIC_API_KEY
    ollama_base_url : str  = ''             # e.g. http://10.0.1.5:11434/v1
    open_design_ref : str  = 'main'         # git branch/tag/commit
    fast_boot       : bool = False          # skip pnpm install+build (baked AMI)

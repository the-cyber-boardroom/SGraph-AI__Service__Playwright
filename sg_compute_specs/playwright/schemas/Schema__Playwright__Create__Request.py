# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — playwright: Schema__Playwright__Create__Request
# Inputs for `sg playwright create`. Pure data.
#
# Containers on the launched node:
#   default            — host-plane + sg-playwright              (2 containers)
#   --with-mitmproxy   — + agent-mitmproxy                       (3 containers)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Playwright__Create__Request(Type_Safe):
    region           : str   = 'eu-west-2'
    instance_type    : str   = 't3.medium'
    from_ami         : str   = ''          # explicit AMI ID; blank = resolve latest AL2023
    stack_name       : str   = ''          # blank = auto-generate
    caller_ip        : str   = ''          # blank = auto-detect
    max_hours        : float = 1.0         # fractional hours supported: 0.1 = 6 min; 0 = no auto-terminate
    with_mitmproxy   : bool  = False        # False = 2 containers; True = + agent-mitmproxy (3 containers)
    intercept_script : str   = ''          # mitmproxy interceptor source — baked into user-data; only meaningful with with_mitmproxy
    image_tag        : str   = 'latest'    # diniscruz/sg-playwright:<tag>
    api_key          : str   = ''          # FAST_API__AUTH__API_KEY__VALUE — auto-generated if blank
    disk_size_gb     : int   = 20          # root volume — container image layers
    use_spot         : bool  = True        # spot by default (~70% cheaper)

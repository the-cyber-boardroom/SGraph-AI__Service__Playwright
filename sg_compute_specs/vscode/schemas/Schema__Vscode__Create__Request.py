# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Schema__Vscode__Create__Request
# Inputs for `sg vscode create`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.primitives.Safe_Int__Disk__GB                          import Safe_Int__Disk__GB
from sg_compute_specs.vscode.enums.Enum__Vscode__Distribution          import Enum__Vscode__Distribution
from sg_compute_specs.vscode.enums.Enum__Vscode__Ingress               import Enum__Vscode__Ingress


class Schema__Vscode__Create__Request(Type_Safe):
    region        : str                        = 'eu-west-2'
    instance_type : str                        = 't3.large'
    from_ami      : str                        = ''             # explicit AMI ID; resolved from helper if blank
    stack_name    : str                        = ''             # empty = auto-generate
    caller_ip     : str                        = ''             # empty = auto-detect (PUBLIC_HTTPS only)
    max_hours     : float                      = 4.0            # auto-terminate; float allows 0.1 = 6 min
    disk_size_gb  : Safe_Int__Disk__GB         = Safe_Int__Disk__GB(100)
    distribution  : Enum__Vscode__Distribution = Enum__Vscode__Distribution.CODE_SERVER
    ingress       : Enum__Vscode__Ingress      = Enum__Vscode__Ingress.SSM_FORWARD
    password      : str                        = ''             # empty = auto-generate; surfaced once at create
    use_spot      : bool                       = True           # spot by default (~70% cheaper)

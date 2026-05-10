# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__CLI__Exec__Result
# Return value from spec.exec() — stdout/stderr, exit code, transport, timing.
# stdout/stderr/error use plain str because Safe_Str normalises spaces and
# newlines to underscores, making log content unreadable.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                        import Type_Safe

from sg_compute.primitives.Safe_Int__Exit__Code             import Safe_Int__Exit__Code


class Schema__CLI__Exec__Result(Type_Safe):
    stdout      : str               = ''
    stderr      : str               = ''
    exit_code   : Safe_Int__Exit__Code
    transport   : str               = 'ssm'    # 'ssm' only (D1)
    duration_ms : int               = 0
    error       : str               = ''

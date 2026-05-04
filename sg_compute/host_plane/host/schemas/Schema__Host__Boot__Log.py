# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Host__Boot__Log
# Returned by GET /host/logs/boot. Tail of cloud-init-output.log.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Host__Boot__Log(Type_Safe):
    source    : str           # absolute path of the log file read
    lines     : int  = 0      # actual number of lines in content
    content   : str           # newline-joined log text; drop into <pre> directly
    truncated : bool = False   # True when file was longer than the requested limit

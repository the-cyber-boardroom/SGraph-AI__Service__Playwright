# ═══════════════════════════════════════════════════════════════════════════════
# Agentic_Boot_State — shared in-memory boot state (v0.1.29)
#
# Holds two pieces of state captured at container start by Agentic_Boot_Shim
# (L2) and exposed to the admin surface by Agentic_Admin_API (L1):
#
#   • A bounded ring buffer of human-readable log lines written by the boot
#     shim — surfaced at GET /admin/boot-log.
#   • The last failed-load error string (empty when the user app imported
#     cleanly) — surfaced at GET /admin/error.
#
# Lives in L1 (`agentic_fastapi/`) on purpose so the L1 admin API does not
# reach into the L2 AWS-specific shim. The shim depends downwards on L1; L1
# knows nothing about L2.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List


BOOT_LOG_MAX_LINES = 200                                                            # Ring-buffer cap — last 200 lines is plenty for a boot trail

_boot_log_lines : List[str] = []                                                    # Module-level; shared across importers by Python's single-module-instance rule
_last_error     : str       = ''


def append_boot_log(line: str) -> None:                                             # Called by the boot shim on each stage
    _boot_log_lines.append(line)
    if len(_boot_log_lines) > BOOT_LOG_MAX_LINES:
        del _boot_log_lines[0]


def get_boot_log() -> List[str]:                                                    # Returns a copy — callers cannot mutate the buffer
    return list(_boot_log_lines)


def set_last_error(error: str) -> None:
    global _last_error
    _last_error = error or ''


def get_last_error() -> str:
    return _last_error


def reset_boot_state() -> None:                                                     # Test hook only — production code never calls this
    global _last_error
    _boot_log_lines.clear()
    _last_error = ''

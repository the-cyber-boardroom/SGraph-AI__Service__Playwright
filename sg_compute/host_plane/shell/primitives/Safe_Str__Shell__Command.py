# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Safe_Str__Shell__Command
# Allowlist-gated shell command primitive. Validation happens at construction
# time so a disallowed command never reaches subprocess.run.
# Regex replaces characters outside [a-zA-Z0-9 _\-./=] to neutralise injection
# attempts that might slip through; the allowlist check is the primary gate.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode

from sg_compute.host_plane.shell.shell_command_allowlist                    import SHELL_COMMAND_ALLOWLIST


class Safe_Str__Shell__Command(Safe_Str):
    regex       = re.compile(r'[^a-zA-Z0-9 _\-./=]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True                                                      # allow empty for Type_Safe default construction; Shell__Executor rejects blank at runtime

    def __new__(cls, value: str = ''):
        if value and not any(value.startswith(prefix) for prefix in SHELL_COMMAND_ALLOWLIST):
            raise ValueError(f'command not in allowlist: {value!r}')
        return super().__new__(cls, value)

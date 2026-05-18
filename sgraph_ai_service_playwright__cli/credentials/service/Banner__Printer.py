# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Banner__Printer
# Prints a single dim stderr line identifying the resolved role and identity.
# Suppressed when quiet=True, enabled=False, or stderr is not a TTY.
# ═══════════════════════════════════════════════════════════════════════════════

import sys

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Banner__Printer(Type_Safe):
    quiet   : bool = False
    enabled : bool = True

    def print(self, role: str, identity_arn: str = '', session_expiry: str = '') -> None:
        if not self.enabled or self.quiet:
            return
        if not sys.stderr.isatty():
            return
        parts = [f'[sg] role={role}']
        if identity_arn:
            parts.append(f'→ {identity_arn}')
        if session_expiry:
            parts.append(f'(expires {session_expiry})')
        print('  \033[2m' + ' '.join(parts) + '\033[0m', file=sys.stderr)

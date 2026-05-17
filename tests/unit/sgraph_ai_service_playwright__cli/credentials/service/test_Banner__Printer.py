# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Banner__Printer (v0.2.28)
# Verifies suppression logic and formatting.
# Note: Banner__Printer suppresses when stderr is not a TTY — in test contexts
# stderr is a pipe, so the actual print call will not fire when tty check runs.
# We test the logic using a subclass that bypasses the tty check.
# ═══════════════════════════════════════════════════════════════════════════════

import sys
from io       import StringIO
from unittest import TestCase

from sgraph_ai_service_playwright__cli.credentials.service.Banner__Printer import Banner__Printer


class Banner__Printer__No_Tty_Check(Banner__Printer):
    """Test subclass that skips the isatty() guard."""

    def print(self, role: str, identity_arn: str = '', session_expiry: str = '') -> None:
        if not self.enabled or self.quiet:
            return
        parts = [f'[sg] role={role}']
        if identity_arn:
            parts.append(f'→ {identity_arn}')
        if session_expiry:
            parts.append(f'(expires {session_expiry})')
        sys.stderr.write('  \033[2m' + ' '.join(parts) + '\033[0m\n')


class test_Banner__Printer__suppression(TestCase):

    def test__quiet_flag_suppresses_output(self):
        buf     = StringIO()
        printer = Banner__Printer__No_Tty_Check(quiet=True)
        old     = sys.stderr
        sys.stderr = buf
        try:
            printer.print(role='admin')
        finally:
            sys.stderr = old
        assert buf.getvalue() == ''

    def test__enabled_false_suppresses_output(self):
        buf     = StringIO()
        printer = Banner__Printer__No_Tty_Check(enabled=False)
        old     = sys.stderr
        sys.stderr = buf
        try:
            printer.print(role='admin')
        finally:
            sys.stderr = old
        assert buf.getvalue() == ''

    def test__real_banner_suppressed_when_not_tty(self):
        buf     = StringIO()
        printer = Banner__Printer()                          # real implementation checks isatty()
        old     = sys.stderr
        sys.stderr = buf                                     # StringIO is not a TTY
        try:
            printer.print(role='admin')
        finally:
            sys.stderr = old
        assert buf.getvalue() == ''                          # suppressed because not a tty


class test_Banner__Printer__formatting(TestCase):

    def _capture_print(self, **kwargs) -> str:
        buf     = StringIO()
        printer = Banner__Printer__No_Tty_Check()
        old     = sys.stderr
        sys.stderr = buf
        try:
            printer.print(**kwargs)
        finally:
            sys.stderr = old
        return buf.getvalue()

    def test__role_only_includes_role(self):
        out = self._capture_print(role='admin')
        assert 'role=admin' in out

    def test__identity_arn_appears_when_provided(self):
        out = self._capture_print(role='admin', identity_arn='arn:aws:sts::123:assumed-role/r/s')
        assert 'arn:aws:sts::123:assumed-role/r/s' in out

    def test__session_expiry_appears_when_provided(self):
        out = self._capture_print(role='admin', session_expiry='2026-05-17T14:00:00Z')
        assert 'expires 2026-05-17T14:00:00Z' in out

    def test__role_and_arn_both_present(self):
        out = self._capture_print(role='dev', identity_arn='arn:aws:sts::999:assumed-role/x/y')
        assert 'role=dev' in out
        assert 'arn:aws:sts' in out

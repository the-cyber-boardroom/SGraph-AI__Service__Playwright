# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Keyring__Mac__OS
# Thin wrapper around /usr/bin/security (macOS Keychain CLI).
# Zero new Python dependencies — subprocess only.
#
# Seam: override _run_security() in tests to avoid real keychain calls.
# ═══════════════════════════════════════════════════════════════════════════════

import subprocess

from osbot_utils.type_safe.Type_Safe                                                           import Type_Safe

from sgraph_ai_service_playwright__cli.osx.keyring.primitives.Safe_Str__Keyring__Account      import Safe_Str__Keyring__Account
from sgraph_ai_service_playwright__cli.osx.keyring.primitives.Safe_Str__Keyring__Service_Name import Safe_Str__Keyring__Service_Name
from sgraph_ai_service_playwright__cli.osx.keyring.schemas.Schema__Keyring__Entry             import Schema__Keyring__Entry


SECURITY_BIN = '/usr/bin/security'


class Keyring__Mac__OS(Type_Safe):

    # ── seam ──────────────────────────────────────────────────────────────────

    def _run_security(self, args: list) -> tuple[int, str, str]:    # (returncode, stdout, stderr)
        try:
            result = subprocess.run([SECURITY_BIN] + args,
                                    capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            return 1, '', f'{SECURITY_BIN} not found (not macOS?)'

    # ── helpers ───────────────────────────────────────────────────────────────

    def _parse_password_line(self, stderr: str) -> str | None:      # security prints password on stderr
        for line in stderr.splitlines():
            if line.startswith('password: '):
                return line[len('password: '):]
        return None

    # ── public API ────────────────────────────────────────────────────────────

    def get(self, service_name: str, account: str) -> str | None:
        rc, stdout, stderr = self._run_security([
            'find-generic-password',
            '-s', service_name,
            '-a', account,
            '-w',                                                    # print password to stdout
        ])
        if rc != 0:
            return None
        return stdout.strip() or None

    def set(self, service_name: str, account: str, value: str) -> bool:
        rc, _, _ = self._run_security([
            'add-generic-password',
            '-s', service_name,
            '-a', account,
            '-w', value,
            '-U',                                                    # update if exists
        ])
        return rc == 0

    def delete(self, service_name: str, account: str) -> bool:
        rc, _, _ = self._run_security([
            'delete-generic-password',
            '-s', service_name,
            '-a', account,
        ])
        return rc == 0

    def list(self, prefix: str = 'sg.') -> list:                     # list[Schema__Keyring__Entry]
        rc, stdout, stderr = self._run_security([
            'dump-keychain',
        ])
        if rc != 0:
            return []
        return self._parse_dump(stdout + stderr, prefix)

    def _parse_dump(self, output: str, prefix: str) -> list:
        entries = []
        current_service  = None
        current_account  = None
        for line in output.splitlines():
            line = line.strip()
            if '"svce"' in line and '<blob>' in line:
                current_service = self._extract_blob_value(line)
            if '"acct"' in line and '<blob>' in line:
                current_account = self._extract_blob_value(line)
            if current_service and current_account:
                if current_service.startswith(prefix):
                    entries.append(Schema__Keyring__Entry(
                        service_name = Safe_Str__Keyring__Service_Name(current_service),
                        account      = Safe_Str__Keyring__Account(current_account)     ,
                    ))
                current_service = None
                current_account = None
        return entries

    def _extract_blob_value(self, line: str) -> str | None:
        if '=' not in line:
            return None
        parts = line.split('=', 1)
        raw   = parts[1].strip()
        if raw.startswith('"') and raw.endswith('"'):
            return raw[1:-1]
        return raw

    def search(self, service_name: str) -> list:                     # list[Schema__Keyring__Entry]
        entries = self.list(prefix='')
        return [e for e in entries if str(e.service_name) == service_name]

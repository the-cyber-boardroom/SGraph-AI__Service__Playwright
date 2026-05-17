# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Keyring__Mac__OS (compatibility shim)
# Re-exports the canonical Keyring__Mac__OS from osx.keyring.service and
# provides Keyring__Mac__OS__In_Memory as an in-process test seam.
#
# Import path used by credentials CLI tests:
#   from sgraph_ai_service_playwright__cli.credentials.service.Keyring__Mac__OS import …
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS import Keyring__Mac__OS  # noqa: F401


class Keyring__Mac__OS__In_Memory(Keyring__Mac__OS):               # test seam — no real keychain calls

    _store: dict = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._store = {}

    def _run_security(self, args: list) -> tuple:
        cmd = args[0] if args else ''

        if cmd == 'find-generic-password':
            service = self._arg(args, '-s')
            account = self._arg(args, '-a')
            value   = self._store.get((service, account))
            if value is None:
                return 1, '', 'not found'
            return 0, value + '\n', ''

        if cmd == 'add-generic-password':
            service = self._arg(args, '-s')
            account = self._arg(args, '-a')
            value   = self._arg(args, '-w')
            self._store[(service, account)] = value
            return 0, '', ''

        if cmd == 'delete-generic-password':
            service = self._arg(args, '-s')
            account = self._arg(args, '-a')
            key     = (service, account)
            if key in self._store:
                del self._store[key]
                return 0, '', ''
            return 1, '', 'not found'

        if cmd == 'dump-keychain':
            return 0, self._fake_dump(), ''

        return 1, '', f'unknown command: {cmd}'

    def _arg(self, args: list, flag: str) -> str:
        try:
            idx = args.index(flag)
            return args[idx + 1]
        except (ValueError, IndexError):
            return ''

    def _fake_dump(self) -> str:
        lines = []
        for (service, account) in self._store:
            lines.append(f'    "svce"<blob>="{service}"')
            lines.append(f'    "acct"<blob>="{account}"')
        return '\n'.join(lines)

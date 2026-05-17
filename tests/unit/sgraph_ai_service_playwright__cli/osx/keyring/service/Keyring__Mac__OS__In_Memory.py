# ═══════════════════════════════════════════════════════════════════════════════
# Test helper — Keyring__Mac__OS__In_Memory
# In-memory subclass of Keyring__Mac__OS that overrides _run_security()
# so tests never touch the real macOS Keychain.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS import Keyring__Mac__OS


class Keyring__Mac__OS__In_Memory(Keyring__Mac__OS):
    _store  : dict = None           # {(service_name, account): value}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._store = {}

    def _run_security(self, args: list) -> tuple:
        cmd = args[0] if args else ''

        if cmd == 'find-generic-password':
            service  = self._arg(args, '-s')
            account  = self._arg(args, '-a')
            value    = self._store.get((service, account))
            if value is None:
                return 1, '', 'not found'
            return 0, value + '\n', ''

        if cmd == 'add-generic-password':
            service  = self._arg(args, '-s')
            account  = self._arg(args, '-a')
            value    = self._arg(args, '-w')
            self._store[(service, account)] = value
            return 0, '', ''

        if cmd == 'delete-generic-password':
            service  = self._arg(args, '-s')
            account  = self._arg(args, '-a')
            key      = (service, account)
            if key in self._store:
                del self._store[key]
                return 0, '', ''
            return 1, '', 'not found'

        if cmd == 'dump-keychain':
            output = self._fake_dump()
            return 0, output, ''

        return 1, '', f'unknown command: {cmd}'

    def _arg(self, args: list, flag: str) -> str:
        try:
            idx = args.index(flag)
            return args[idx + 1]
        except (ValueError, IndexError):
            return ''

    def _fake_dump(self) -> str:
        lines = []
        for (service, account), _ in self._store.items():
            lines.append(f'    "svce"<blob>="{service}"')
            lines.append(f'    "acct"<blob>="{account}"')
        return '\n'.join(lines)

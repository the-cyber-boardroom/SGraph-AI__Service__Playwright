# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Credentials — Toml__Projector
#
# Generates a human-editable TOML text from the current state in
# Credentials__Store. Secrets are replaced with '********' unless they are
# non-sensitive (e.g., access key IDs that start with 'AKIA').
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                       import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store             import Credentials__Store
from sgraph_ai_service_playwright__cli.credentials.edit.Schema__Edit__Snapshot            import Schema__Edit__Snapshot, SENTINEL


def _toml_str(v: str) -> str:                                                    # safely quote a TOML string value
    return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _cfg_to_dict(cfg) -> dict:                                                   # Schema__AWS__Role__Config → plain dict
    if cfg is None:
        return {}
    if hasattr(cfg, 'region'):
        return {'region'         : str(cfg.region)          ,
                'assume_role_arn': str(cfg.assume_role_arn)  ,
                'session_name'   : str(cfg.session_name)     }
    return cfg if isinstance(cfg, dict) else {}


def _creds_to_dict(creds) -> dict:                                               # Schema__AWS__Credentials → plain dict
    if creds is None:
        return {}
    if hasattr(creds, 'access_key'):
        return {'access_key': str(creds.access_key) ,
                'secret_key': str(creds.secret_key) }
    return creds if isinstance(creds, dict) else {}


class Toml__Projector(Type_Safe):

    store: Credentials__Store

    def project(self) -> str:                                                    # returns TOML text ready for editing
        lines = []
        lines.append('# SG credentials — edit mode')
        lines.append("# Secrets show as '********'. Replace the value to change; leave '********' to keep unchanged.")
        lines.append('')

        # ── roles ─────────────────────────────────────────────────────────────
        role_names = self.store.role_list()
        for role in role_names:
            cfg = _cfg_to_dict(self.store.role_get(role))
            lines.append(f'[roles.{role}]')
            lines.append(f'region          = {_toml_str(cfg.get("region","us-east-1"))}')
            lines.append(f'assume_role_arn = {_toml_str(cfg.get("assume_role_arn",""))}')
            lines.append(f'session_name    = {_toml_str(cfg.get("session_name",""))}')
            lines.append('')

        # ── aws credentials ───────────────────────────────────────────────────
        for role in role_names:
            creds      = _creds_to_dict(self.store.aws_credentials_get(role))
            access_key = creds.get('access_key', '')
            lines.append(f'[aws_credentials.{role}]')
            if access_key.startswith(('AKIA', 'ASIA', 'AROA', 'AIDA')):
                lines.append(f'access_key = {_toml_str(access_key)}')
            else:
                lines.append(f'access_key = {_toml_str(SENTINEL)}')
            lines.append(f'secret_key = {_toml_str(SENTINEL)}  # (sealed — replace to change)')
            lines.append('')

        # ── vault keys ────────────────────────────────────────────────────────
        vault_names = self.store.vault_key_list()
        if vault_names:
            lines.append('[vault_keys]')
            for name in vault_names:
                lines.append(f'{name} = {_toml_str(SENTINEL)}')
            lines.append('')

        # ── secrets (scan all known secret namespaces) ────────────────────────
        secret_entries = self.store.keyring.list(prefix='sg.secret.')
        ns_map: dict = {}
        for entry in secret_entries:
            svc = str(entry.service_name)
            ns  = svc[len('sg.secret.'):]
            ns_map.setdefault(ns, []).append(str(entry.account))
        for ns in sorted(ns_map):
            lines.append(f'[secrets.{ns}]')
            for name in sorted(ns_map[ns]):
                lines.append(f'{name} = {_toml_str(SENTINEL)}')
            lines.append('')

        return '\n'.join(lines)

    def snapshot(self) -> Schema__Edit__Snapshot:                                # current state as a snapshot
        roles           = {}
        aws_credentials = {}
        vault_keys      = {}
        secrets         = {}

        for role in self.store.role_list():
            roles[role] = _cfg_to_dict(self.store.role_get(role))

        for role in self.store.role_list():
            creds = _creds_to_dict(self.store.aws_credentials_get(role))
            aws_credentials[role] = {'access_key': creds.get('access_key', ''),
                                     'secret_key': creds.get('secret_key', '')}

        for name in self.store.vault_key_list():
            vault_keys[name] = self.store.vault_key_get(name) or ''

        for entry in self.store.keyring.list(prefix='sg.secret.'):
            svc  = str(entry.service_name)
            ns   = svc[len('sg.secret.'):]
            name = str(entry.account)
            secrets.setdefault(ns, {})[name] = self.store.secret_get(ns, name) or ''

        return Schema__Edit__Snapshot(roles           = roles           ,
                                      aws_credentials = aws_credentials ,
                                      vault_keys      = vault_keys      ,
                                      secrets         = secrets         )

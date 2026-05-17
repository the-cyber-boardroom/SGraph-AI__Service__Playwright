# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Credentials — Toml__Parser
#
# Parses a TOML text back into a Schema__Edit__Snapshot.
# Uses tomllib (Python 3.11+ stdlib). Returns (snapshot, None) on success
# or (None, error_str) on any parse failure.
# ═══════════════════════════════════════════════════════════════════════════════

import tomllib

from osbot_utils.type_safe.Type_Safe                                                       import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.edit.Schema__Edit__Snapshot            import Schema__Edit__Snapshot


class Toml__Parser(Type_Safe):

    def parse(self, text: str) -> tuple:                                         # (Schema__Edit__Snapshot, None) | (None, str)
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as e:
            return None, f'TOML parse error: {e}'

        roles           = {}
        aws_credentials = {}
        vault_keys      = {}
        secrets         = {}

        for name, cfg in (data.get('roles') or {}).items():
            roles[name] = {'region'         : str(cfg.get('region',          'us-east-1')) ,
                           'assume_role_arn': str(cfg.get('assume_role_arn', ''))          ,
                           'session_name'   : str(cfg.get('session_name',    ''))          }

        for role, creds in (data.get('aws_credentials') or {}).items():
            aws_credentials[role] = {'access_key': str(creds.get('access_key', '')),
                                     'secret_key': str(creds.get('secret_key', ''))}

        for name, value in (data.get('vault_keys') or {}).items():
            vault_keys[name] = str(value)

        for ns, entries in (data.get('secrets') or {}).items():
            secrets[ns] = {name: str(v) for name, v in entries.items()}

        snap = Schema__Edit__Snapshot(roles           = roles           ,
                                      aws_credentials = aws_credentials ,
                                      vault_keys      = vault_keys      ,
                                      secrets         = secrets         )
        return snap, None

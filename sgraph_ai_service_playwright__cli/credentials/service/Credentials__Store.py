# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Credentials__Store
# High-level credential operations backed by Keyring__Mac__OS.
# Translates between logical names (roles, AWS keys, vault keys) and
# the namespaced keyring service name format (sg.config.role.<name>, etc.).
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.enums.Enum__Credential__Kind                import Enum__Credential__Kind
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Access__Key       import Safe_Str__AWS__Access__Key
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Secret__Key       import Safe_Str__AWS__Secret__Key
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name             import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Credentials            import Schema__AWS__Credentials
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__AWS__Role__Config           import Schema__AWS__Role__Config
from sgraph_ai_service_playwright__cli.osx.keyring.enums.Enum__Keyring__Service                import Enum__Keyring__Service
from sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS                    import Keyring__Mac__OS


_ACCOUNT_ACCESS_KEY  = 'access_key'
_ACCOUNT_SECRET_KEY  = 'secret_key'
_ACCOUNT_CONFIG      = 'config'


class Credentials__Store(Type_Safe):
    keyring     : Keyring__Mac__OS

    # ── keyring service name helpers ──────────────────────────────────────────

    def _role_service_name(self, role_name: str) -> str:
        return f'{Enum__Keyring__Service.ROLE}.{role_name}'

    def _aws_access_key_service(self, role_name: str) -> str:
        return f'{Enum__Keyring__Service.AWS_ROLE}.{role_name}'

    def _vault_service_name(self, vault_name: str) -> str:
        return f'{Enum__Keyring__Service.VAULT}.{vault_name}'

    def _secret_service_name(self, ns: str, name: str) -> str:
        return f'{Enum__Keyring__Service.SECRET}.{ns}.{name}'

    # ── role config ───────────────────────────────────────────────────────────

    def role_set(self, config: Schema__AWS__Role__Config) -> bool:
        service  = self._role_service_name(str(config.name))
        payload  = json.dumps({'name'           : str(config.name           ),
                               'region'         : str(config.region         ),
                               'assume_role_arn': str(config.assume_role_arn),
                               'session_name'   : str(config.session_name   ),
                               'account_id'     : str(config.account_id     )})
        return self.keyring.set(service, _ACCOUNT_CONFIG, payload)

    def role_get(self, role_name: str) -> Schema__AWS__Role__Config | None:
        service = self._role_service_name(role_name)
        raw     = self.keyring.get(service, _ACCOUNT_CONFIG)
        if raw is None:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return Schema__AWS__Role__Config(
            name            = Safe_Str__Role__Name(data.get('name'           , '')),
            region          = data.get('region'         , ''),
            assume_role_arn = data.get('assume_role_arn', ''),
            session_name    = data.get('session_name'   , ''),
            account_id      = data.get('account_id'     , ''),
        )

    def role_delete(self, role_name: str) -> bool:
        service      = self._role_service_name(role_name)
        deleted_cfg  = self.keyring.delete(service, _ACCOUNT_CONFIG)
        deleted_aws  = self.aws_credentials_delete(role_name)
        return deleted_cfg or deleted_aws

    def role_list(self) -> list:                           # list[str] — role names, sorted
        prefix  = f'{Enum__Keyring__Service.ROLE}.'
        entries = self.keyring.list(prefix=prefix)
        names   = []
        for entry in entries:
            svc = str(entry.service_name)
            if svc.startswith(prefix):
                name = svc[len(prefix):]
                if name and name not in names:
                    names.append(name)
        return sorted(names)

    # ── aws credentials ───────────────────────────────────────────────────────

    def aws_credentials_set(self, role_name: str, access_key: str, secret_key: str) -> bool:
        service     = self._aws_access_key_service(role_name)
        ok_access   = self.keyring.set(service, _ACCOUNT_ACCESS_KEY, access_key)
        ok_secret   = self.keyring.set(service, _ACCOUNT_SECRET_KEY, secret_key)
        return ok_access and ok_secret

    def aws_credentials_get(self, role_name: str) -> Schema__AWS__Credentials | None:
        service     = self._aws_access_key_service(role_name)
        access_key  = self.keyring.get(service, _ACCOUNT_ACCESS_KEY)
        secret_key  = self.keyring.get(service, _ACCOUNT_SECRET_KEY)
        if access_key is None or secret_key is None:
            return None
        return Schema__AWS__Credentials(
            role_name  = Safe_Str__Role__Name(role_name)       ,
            access_key = Safe_Str__AWS__Access__Key(access_key) ,
            secret_key = Safe_Str__AWS__Secret__Key(secret_key) ,
        )

    def aws_credentials_delete(self, role_name: str) -> bool:
        service     = self._aws_access_key_service(role_name)
        ok_access   = self.keyring.delete(service, _ACCOUNT_ACCESS_KEY)
        ok_secret   = self.keyring.delete(service, _ACCOUNT_SECRET_KEY)
        return ok_access or ok_secret

    # ── vault keys ────────────────────────────────────────────────────────────

    def vault_set(self, vault_name: str, vault_key: str) -> bool:
        service = self._vault_service_name(vault_name)
        return self.keyring.set(service, vault_name, vault_key)

    def vault_get(self, vault_name: str) -> str | None:
        service = self._vault_service_name(vault_name)
        return self.keyring.get(service, vault_name)

    def vault_delete(self, vault_name: str) -> bool:
        service = self._vault_service_name(vault_name)
        return self.keyring.delete(service, vault_name)

    def vault_list(self) -> list:                               # list[str] — vault names
        prefix  = f'{Enum__Keyring__Service.VAULT}.'
        entries = self.keyring.list(prefix=prefix)
        names   = []
        for entry in entries:
            svc = str(entry.service_name)
            if svc.startswith(prefix):
                name = svc[len(prefix):]
                if name and name not in names:
                    names.append(name)
        return sorted(names)

    vault_key_set    = vault_set                                # convenience aliases
    vault_key_get    = vault_get
    vault_key_delete = vault_delete
    vault_key_list   = vault_list

    # ── arbitrary secrets ─────────────────────────────────────────────────────

    def secret_set(self, ns: str, name: str, value: str) -> bool:
        service = self._secret_service_name(ns, name)
        return self.keyring.set(service, name, value)

    def secret_get(self, ns: str, name: str) -> str | None:
        service = self._secret_service_name(ns, name)
        return self.keyring.get(service, name)

    def secret_delete(self, ns: str, name: str) -> bool:
        service = self._secret_service_name(ns, name)
        return self.keyring.delete(service, name)

    def secret_list(self, ns: str) -> list:                     # list[str] — names in namespace
        prefix  = f'{Enum__Keyring__Service.SECRET}.{ns}.'
        entries = self.keyring.list(prefix=prefix)
        names   = sorted({str(e.account) for e in entries
                          if str(e.service_name).startswith(prefix) and str(e.account)})
        return names

    # ── route mappings ────────────────────────────────────────────────────────

    def routes_set(self, routes: list) -> bool:                    # list[dict]
        payload = json.dumps(routes)
        return self.keyring.set(str(Enum__Keyring__Service.ROUTES), 'routes', payload)

    def routes_get(self) -> list:                                  # list[dict]
        raw = self.keyring.get(str(Enum__Keyring__Service.ROUTES), 'routes')
        if raw is None:
            return []
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []

    def route_add(self, pattern: str, role: str) -> bool:          # append {pattern, role} entry
        routes = self.routes_get()
        routes.append({'pattern': pattern, 'role': role})
        return self.routes_set(routes)

    def route_delete(self, pattern: str) -> bool:                  # remove first entry matching pattern
        routes  = self.routes_get()
        updated = [r for r in routes if r.get('pattern') != pattern]
        if len(updated) == len(routes):
            return False
        self.routes_set(updated)
        return True

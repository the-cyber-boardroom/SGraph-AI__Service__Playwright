# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Credentials__Resolver
# Dry-run resolver: resolves which role and credentials would handle a command.
# No AWS calls — pure in-memory resolution using the stored config.
# ═══════════════════════════════════════════════════════════════════════════════

import fnmatch

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__Trace__Result import Schema__Trace__Result
from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store    import Credentials__Store


class Credentials__Resolver(Type_Safe):
    store : Credentials__Store

    # ── route matching ────────────────────────────────────────────────────────

    def _match_route(self, command_path: list, routes: list) -> tuple:
        path_str = ' '.join(command_path)
        for route in routes:
            pattern  = route.get('pattern', route.get('from', ''))
            role     = route.get('role',    route.get('to',   ''))
            if pattern and role:
                if fnmatch.fnmatch(path_str, pattern):
                    return pattern, role
        return '', ''

    # ── role chain resolution ─────────────────────────────────────────────────

    def _resolve_chain(self, role_name: str, visited: set = None) -> list:
        if visited is None:
            visited = set()
        if role_name in visited:
            return [role_name]                                      # cycle guard
        visited.add(role_name)
        config = self.store.role_get(role_name)
        if config is None:
            return [role_name]
        assume_arn = str(config.assume_role_arn)
        if not assume_arn:
            return [role_name]                                      # direct creds — no chain
        source_creds = self.store.aws_credentials_get(role_name)
        if source_creds is not None:
            return [role_name]                                      # has own creds + assume_arn → self is source
        default_config = self.store.role_get('default')
        if default_config is not None and role_name != 'default':
            return ['default', role_name]
        return [role_name]

    # ── source creds description ──────────────────────────────────────────────

    def _source_creds_description(self, role_name: str) -> str:
        if not role_name:
            return 'not found'
        chain  = self._resolve_chain(role_name)
        source = chain[0] if chain else role_name
        creds  = self.store.aws_credentials_get(source)
        if creds is None:
            return 'not found'
        from sgraph_ai_service_playwright__cli.osx.keyring.enums.Enum__Keyring__Service import Enum__Keyring__Service
        svc = f'{Enum__Keyring__Service.AWS_ROLE}.{source}'
        return f'keyring ({svc}.access_key)'

    # ── public API ────────────────────────────────────────────────────────────

    def trace(self, command_path: list) -> Schema__Trace__Result:
        routes               = self.store.routes_get()
        matched_route, matched_role = self._match_route(command_path, routes)
        role_chain           = self._resolve_chain(matched_role) if matched_role else []
        would_assume_arn     = ''
        if matched_role:
            config = self.store.role_get(matched_role)
            if config:
                would_assume_arn = str(config.assume_role_arn)
        session_name_tmpl    = f'sg-{matched_role}-<ts>-<uuid>' if matched_role else ''
        source_creds_str     = self._source_creds_description(matched_role)
        return Schema__Trace__Result(
            command_path      = list(command_path)  ,
            matched_route     = matched_route        ,
            matched_role      = matched_role         ,
            role_chain        = role_chain           ,
            would_assume_arn  = would_assume_arn     ,
            session_name_tmpl = session_name_tmpl    ,
            source_creds      = source_creds_str     ,
        )

# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Credentials__Loader (v0.1.24 — stateless)
#
# Vault-to-browser-context glue. Reads cookies / storage state from the vault
# (via Artefact__Writer's seams) and applies them to a Playwright BrowserContext
# the caller passes in directly. No Session__Manager indirection.
#
# Contract:
#   • Holds NO vault client — reaches the vault via Artefact__Writer.
#   • Never calls page.*   — only context.add_cookies / context.set_extra_http_headers.
#   • Missing context is a silent no-op (caller error, not a 500).
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                          import Any

from osbot_utils.type_safe.Type_Safe                                                                 import Type_Safe

from sgraph_ai_service_playwright.schemas.artefact.Schema__Vault_Ref                                 import Schema__Vault_Ref
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Credentials                      import Schema__Session__Credentials
from sgraph_ai_service_playwright.service.Artefact__Writer                                           import Artefact__Writer


class Credentials__Loader(Type_Safe):

    artefact_writer : Artefact__Writer = None                                       # Injected — exposes read_from_vault / write_to_vault seams

    def apply(self                                                      ,
              context     : Any                                         ,           # Playwright BrowserContext
              credentials : Schema__Session__Credentials
         ) -> None:

        if context is None or credentials is None:
            return

        if credentials.cookies_vault_ref:
            cookies = self.artefact_writer.read_from_vault(credentials.cookies_vault_ref)
            if cookies:
                context.add_cookies(cookies)

        if credentials.storage_state_vault_ref:
            state = self.artefact_writer.read_from_vault(credentials.storage_state_vault_ref)
            if state and 'cookies' in state:
                context.add_cookies(state['cookies'])

        if credentials.extra_http_headers:
            headers = {str(k): str(v) for k, v in credentials.extra_http_headers.items()}
            context.set_extra_http_headers(headers)

    def save_state_to_vault(self                                ,
                            vault_ref : Schema__Vault_Ref       ,
                            state     : dict
                       ) -> None:
        self.artefact_writer.write_to_vault(vault_ref, state)

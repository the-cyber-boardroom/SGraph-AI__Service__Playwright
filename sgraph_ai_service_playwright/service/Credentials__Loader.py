# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Credentials__Loader (v2 spec §4.7; full source in pack)
#
# Vault-to-browser-context glue. Reads cookies and storage state from the vault
# (via Artefact__Writer's read_from_vault seam) and applies them to the
# session's Playwright BrowserContext. Also persists state back via
# save_state_to_vault → Artefact__Writer.write_to_vault.
#
# Contract boundaries:
#   • This class holds NO vault client — it goes through Artefact__Writer.
#   • This class does NOT call page.*   — it only touches context.add_cookies
#     and context.set_extra_http_headers (which is context-level, not page.*).
#     Consistent with the spec's §10 rule ("Step__Executor is the only class
#     that calls page.*") since cookies/headers are context-scoped.
#   • Missing session / browser is a silent no-op (caller error, not a 500).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                             import Type_Safe

from sgraph_ai_service_playwright.schemas.artefact.Schema__Vault_Ref                             import Schema__Vault_Ref
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                       import Session_Id
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Credentials                   import Schema__Session__Credentials
from sgraph_ai_service_playwright.service.Artefact__Writer                                        import Artefact__Writer
from sgraph_ai_service_playwright.service.Session__Manager                                        import Session__Manager


class Credentials__Loader(Type_Safe):

    artefact_writer : Artefact__Writer = None                                       # Injected — exposes read_from_vault / write_to_vault seams

    def apply(self                                                       ,
              session_id      : Session_Id                               ,
              session_manager : Session__Manager                         ,
              credentials     : Schema__Session__Credentials
         ) -> None:

        browser = session_manager.get_browser(session_id)
        if browser is None:                                                         # Session gone or never had a live browser — nothing to do
            return

        contexts = browser.contexts()
        if not contexts:                                                            # Launcher guarantees one context, but belt-and-braces
            return
        context = contexts[0]

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

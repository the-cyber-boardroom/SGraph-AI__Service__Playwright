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
#   • THE ONLY class that calls context.add_cookies — the set_cookie step verb
#     also lands here (add_cookie below), dispatched by Step__Executor with the
#     per-request page.context. Stateless: that context is fresh for this request
#     and discarded after it, so the cookie never outlives the request.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                          import Any

from osbot_utils.type_safe.Type_Safe                                                                 import Type_Safe

from sg_compute_specs.playwright.core.schemas.artefact.Schema__Vault_Ref                                 import Schema__Vault_Ref
from sg_compute_specs.playwright.core.schemas.session.Schema__Session__Credentials                      import Schema__Session__Credentials
from sg_compute_specs.playwright.core.schemas.steps.Schema__Step__Set_Cookie                            import Schema__Step__Set_Cookie
from sg_compute_specs.playwright.core.service.Artefact__Writer                                           import Artefact__Writer


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

    def add_cookie(self                                 ,                           # set_cookie step verb — builds the Playwright cookie dict and applies it
                   context : Any                        ,                           # Playwright BrowserContext (per-request, fresh — cookie dies with it)
                   step    : Schema__Step__Set_Cookie
              ) -> None:

        if context is None or step is None:                                         # Same silent no-op contract as apply()
            return

        cookie = {'name' : str(step.name) ,                                         # Omit-None build: only fields the caller set reach Playwright
                  'value': str(step.value)}
        if step.url:                                                                # URL form — Playwright derives domain + path
            cookie['url'] = str(step.url)
        else:                                                                       # Domain form — path defaults to '/' (validator guarantees domain is set here)
            cookie['domain'] = str(step.domain)
            cookie['path']   = str(step.path) if step.path else '/'
        cookie['secure']   = bool(step.secure)
        cookie['httpOnly'] = bool(step.http_only)
        if step.same_site is not None:
            cookie['sameSite'] = step.same_site.value                               # Enum → capitalised value ("Strict"/"Lax"/"None")
        if step.expires is not None:
            cookie['expires'] = int(step.expires)

        context.add_cookies([cookie])

    def save_state_to_vault(self                                ,
                            vault_ref : Schema__Vault_Ref       ,
                            state     : dict
                       ) -> None:
        self.artefact_writer.write_to_vault(vault_ref, state)

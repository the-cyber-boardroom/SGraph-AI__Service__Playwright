# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Page__Factory
#
# THE canonical way to get a `Page` from a freshly-launched `Browser`. Single
# source of truth for context-creation policy:
#   • ignore_https_errors honoured when SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS is set
#     (EC2 sidecar deployments that proxy TLS through agent_mitmproxy)
#   • returns the first existing page if the browser already has one, otherwise
#     creates a fresh context + page
#
# WHY this module exists:
#   Before this extraction Sequence__Runner.get_or_create_page and
#   Session__Registry._get_or_create_page each had their own copy of the
#   page-creation logic. They drifted: Sequence had the env-var check, Session
#   didn't. Result: /session/* navigation hit ERR_CERT_AUTHORITY_INVALID on
#   vault URLs while /sequence/execute against the SAME url worked. Caught by
#   the @Content debrief 2026-05-31 (ISSUE-A).
#
#   ANY new caller that needs a `Page` from a `Browser` MUST use this factory.
#   The Page__Factory tests include a discipline guard that scans the
#   codebase for raw `browser.new_context(` calls and fails if any appear
#   outside this file — keeps the next blind spot from reopening.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import Any, Dict

from osbot_utils.utils.Env                                                                          import get_env

from sg_compute_specs.playwright.core.consts.env_vars                                                   import ENV_VAR__IGNORE_HTTPS_ERRORS


def context_kwargs_from_env() -> Dict[str, Any]:                                    # Single source of truth for context-creation options driven by env vars
    kwargs : Dict[str, Any] = {}
    if get_env(ENV_VAR__IGNORE_HTTPS_ERRORS):                                       # Set on EC2 when the agent_mitmproxy sidecar does TLS interception
        kwargs['ignore_https_errors'] = True
    return kwargs


def get_or_create_page(browser: Any) -> Any:                                        # The ONLY supported way to get a Page from a Browser in this codebase
    contexts = browser.contexts                                                     # Playwright sync API: `contexts` is a @property returning List[BrowserContext]
    if contexts:
        context = contexts[0]
    else:
        context = browser.new_context(**context_kwargs_from_env())
    pages = context.pages
    if pages:
        return pages[0]
    return context.new_page()

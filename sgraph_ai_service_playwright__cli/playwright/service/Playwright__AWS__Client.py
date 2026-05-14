# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright__AWS__Client
# Composition shell for the per-concern AWS helpers (SG / AMI / Instance /
# Tags / Launch). Mirrors Vnc__AWS__Client.
# Owns the tag-key constants and the PLAYWRIGHT_NAMING binding so the
# section's AWS surface lives in one shared header.
#
# Tag convention:
#   sg:purpose          : playwright
#   sg:stack-name       : {stack_name}          ← logical name lookup
#   sg:allowed-ip       : {caller_ip}           ← records what /32 was set
#   sg:creator          : git email or $USER
#   sg:section          : playwright
#   sg:with-mitmproxy   : true | false          ← mitmproxy opt-in flag
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                         import Stack__Naming


TAG_PURPOSE_KEY          = 'sg:purpose'
TAG_PURPOSE_VALUE        = 'playwright'
TAG_STACK_NAME_KEY       = 'sg:stack-name'
TAG_ALLOWED_IP_KEY       = 'sg:allowed-ip'
TAG_CREATOR_KEY          = 'sg:creator'
TAG_SECTION_KEY          = 'sg:section'
TAG_SECTION_VALUE        = 'playwright'
TAG_WITH_MITMPROXY_KEY   = 'sg:with-mitmproxy'


PLAYWRIGHT_NAMING = Stack__Naming(section_prefix='playwright')                   # AWS Name tag carries 'playwright-' prefix; never doubled


class Playwright__AWS__Client(Type_Safe):                                        # Composes the per-concern helpers — kept small on purpose
    sg       : object = None                                                     # Playwright__SG__Helper       (lazy via setup())
    ami      : object = None                                                     # Playwright__AMI__Helper      (lazy via setup())
    instance : object = None                                                     # Playwright__Instance__Helper (lazy via setup())
    tags     : object = None                                                     # Playwright__Tags__Builder    (lazy via setup())
    launch   : object = None                                                     # Playwright__Launch__Helper   (lazy via setup())

    def setup(self) -> 'Playwright__AWS__Client':                                # Lazy import — avoids circular module-load when callers import the client first
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__SG__Helper       import Playwright__SG__Helper
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__AMI__Helper      import Playwright__AMI__Helper
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Instance__Helper import Playwright__Instance__Helper
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Launch__Helper   import Playwright__Launch__Helper
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Tags__Builder    import Playwright__Tags__Builder
        self.sg       = Playwright__SG__Helper      ()
        self.ami      = Playwright__AMI__Helper     ()
        self.instance = Playwright__Instance__Helper()
        self.tags     = Playwright__Tags__Builder   ()
        self.launch   = Playwright__Launch__Helper  ()
        return self

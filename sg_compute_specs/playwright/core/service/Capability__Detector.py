# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Capability__Detector (spec §4.6)
#
# Detects the deployment target from environment variables and builds a
# Schema__Service__Capabilities describing what that target can do. Also
# surfaces the Schema__Service__Info payload for the /info route and a basic
# connectivity Schema__Health__Check for the /health route.
# ═══════════════════════════════════════════════════════════════════════════════

from importlib.metadata                                                                             import PackageNotFoundError, version as pkg_version
from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version                     import Safe_Str__Version
from osbot_utils.utils.Env                                                                          import get_env

from sg_compute_specs.playwright.core.consts.env_vars                                                   import (ENV_VAR__AGENTIC_CODE_SOURCE   ,
                                                                                                            ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                            ENV_VAR__CHROMIUM_EXECUTABLE   ,
                                                                                                            ENV_VAR__CI                    ,
                                                                                                            ENV_VAR__CLAUDE_SESSION        ,
                                                                                                            ENV_VAR__DEFAULT_PROXY_URL     ,
                                                                                                            ENV_VAR__DEFAULT_S3_BUCKET     ,
                                                                                                            ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                            ENV_VAR__SG_SEND_BASE_URL      )
from sg_compute_specs.playwright.core.consts.image_version                                              import image_version__sgraph_ai_service_playwright
from sg_compute_specs.playwright.core.consts.version                                                    import version__sgraph_ai_service_playwright
from sg_compute_specs.playwright.core.schemas.enums.Enum__Artefact__Sink                                import Enum__Artefact__Sink
from sg_compute_specs.playwright.core.schemas.enums.Enum__Browser__Name                                 import Enum__Browser__Name
from sg_compute_specs.playwright.core.schemas.enums.Enum__Deployment__Target                            import Enum__Deployment__Target
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Version__Browser                import Safe_Str__Version__Browser
from sg_compute_specs.playwright.core.schemas.service.Schema__Health__Check                             import Schema__Health__Check
from sg_compute_specs.playwright.core.schemas.service.Schema__Service__Capabilities                     import Schema__Service__Capabilities
from sg_compute_specs.playwright.core.schemas.service.Schema__Service__Info                             import Schema__Service__Info


FALLBACK_VERSION     = '0.0.0'                                                      # Safe_Str__Version rejects 'unknown'; use a sentinel instead
FALLBACK_CODE_SOURCE = 'passthrough:sys.path'                                       # When the boot shim hasn't run (local dev, direct uvicorn, tests)


class Capability__Detector(Type_Safe):

    detected_target       : Enum__Deployment__Target      = None
    detected_capabilities : Schema__Service__Capabilities = None

    def detect(self) -> 'Capability__Detector':
        self.detected_target       = self.detect_target()
        self.detected_capabilities = self.build_capabilities(self.detected_target)
        return self

    def target(self) -> Enum__Deployment__Target:
        return self.detected_target

    def capabilities(self) -> Schema__Service__Capabilities:
        return self.detected_capabilities

    def service_info(self) -> Schema__Service__Info:
        return Schema__Service__Info(service_name       = 'sg-playwright'                          ,
                                     service_version    = version__sgraph_ai_service_playwright    ,
                                     image_version      = image_version__sgraph_ai_service_playwright,
                                     playwright_version = self.detect_playwright_version()         ,
                                     chromium_version   = self.detect_chromium_version()           ,
                                     deployment_target  = self.detected_target                     ,
                                     capabilities       = self.detected_capabilities               ,
                                     code_source        = self.detect_code_source()                )

    def detect_code_source(self) -> str:                                            # Boot shim writes AGENTIC_CODE_SOURCE; fallback means shim didn't run
        return get_env(ENV_VAR__AGENTIC_CODE_SOURCE) or FALLBACK_CODE_SOURCE

    def detect_target(self) -> Enum__Deployment__Target:
        explicit = get_env(ENV_VAR__DEPLOYMENT_TARGET)
        if explicit:
            return Enum__Deployment__Target(explicit)
        if get_env(ENV_VAR__AWS_LAMBDA_RUNTIME_API):
            return Enum__Deployment__Target.LAMBDA
        if get_env(ENV_VAR__CLAUDE_SESSION):
            return Enum__Deployment__Target.CLAUDE_WEB
        if get_env(ENV_VAR__CI):
            return Enum__Deployment__Target.CI
        return Enum__Deployment__Target.LAPTOP

    def build_capabilities(self, target: Enum__Deployment__Target) -> Schema__Service__Capabilities:
        builder = getattr(self, f'capabilities__{target.value}', None)
        if builder:
            return builder()
        return self.capabilities__laptop()                                          # Safe fallback

    def capabilities__lambda(self) -> Schema__Service__Capabilities:
        return Schema__Service__Capabilities(max_session_lifetime_ms = 900_000                                       ,
                                             supports_persistent     = False                                         ,
                                             supports_video          = True                                          ,
                                             available_browsers      = [Enum__Browser__Name.CHROMIUM                 ,   # Firefox + WebKit come with mcr.microsoft.com/playwright/python:v1.58.0-noble (same image, all three engines pre-installed)
                                                                        Enum__Browser__Name.FIREFOX                  ,
                                                                        Enum__Browser__Name.WEBKIT                   ],
                                             supported_sinks         = [Enum__Artefact__Sink.VAULT                   ,
                                                                        Enum__Artefact__Sink.INLINE                  ,
                                                                        Enum__Artefact__Sink.S3                      ],
                                             memory_budget_mb        = 5120                                          ,
                                             has_vault_access        = bool(get_env(ENV_VAR__SG_SEND_BASE_URL))      ,
                                             has_s3_access           = True                                          ,
                                             has_network_egress      = True                                          ,
                                             proxy_configured        = bool(get_env(ENV_VAR__DEFAULT_PROXY_URL))     )

    def capabilities__claude_web(self) -> Schema__Service__Capabilities:
        return Schema__Service__Capabilities(max_session_lifetime_ms = 600_000                                       ,
                                             supports_persistent     = False                                         ,
                                             supports_video          = True                                          ,
                                             available_browsers      = [Enum__Browser__Name.CHROMIUM]                ,
                                             supported_sinks         = [Enum__Artefact__Sink.INLINE]                 ,
                                             memory_budget_mb        = 4096                                          ,
                                             has_vault_access        = False                                         ,
                                             has_s3_access           = False                                         ,
                                             has_network_egress      = True                                          ,
                                             proxy_configured        = True                                          )

    def capabilities__laptop(self) -> Schema__Service__Capabilities:
        return Schema__Service__Capabilities(max_session_lifetime_ms = 14_400_000                                    ,
                                             supports_persistent     = True                                          ,
                                             supports_video          = True                                          ,
                                             available_browsers      = [Enum__Browser__Name.CHROMIUM                 ,
                                                                        Enum__Browser__Name.FIREFOX                  ,
                                                                        Enum__Browser__Name.WEBKIT                   ],
                                             supported_sinks         = [Enum__Artefact__Sink.VAULT                   ,
                                                                        Enum__Artefact__Sink.INLINE                  ,
                                                                        Enum__Artefact__Sink.S3                      ,
                                                                        Enum__Artefact__Sink.LOCAL_FILE               ],
                                             memory_budget_mb        = 16384                                         ,
                                             has_vault_access        = bool(get_env(ENV_VAR__SG_SEND_BASE_URL))      ,
                                             has_s3_access           = bool(get_env(ENV_VAR__DEFAULT_S3_BUCKET))     ,
                                             has_network_egress      = True                                          ,
                                             proxy_configured        = bool(get_env(ENV_VAR__DEFAULT_PROXY_URL))     )

    def capabilities__ci(self) -> Schema__Service__Capabilities:
        base = self.capabilities__laptop()
        base.supports_persistent     = False
        base.max_session_lifetime_ms = 600_000
        return base

    def capabilities__container(self) -> Schema__Service__Capabilities:
        return self.capabilities__laptop()                                          # Container has same profile as laptop

    def detect_playwright_version(self) -> Safe_Str__Version:                       # Uses importlib.metadata — playwright has no __version__ attr
        try:
            return Safe_Str__Version(pkg_version('playwright'))
        except PackageNotFoundError:
            return Safe_Str__Version(FALLBACK_VERSION)

    # F1 — the old probe opened sync_playwright() inside the running service; under
    # uvicorn's asyncio loop the sync API raises ("Sync API inside asyncio loop"),
    # landing in the except → FALLBACK_VERSION on every deployment. Never launch
    # Playwright from a health probe: read the pip package's bundled driver
    # metadata instead (pure file read — fast, loop-safe, exception-safe).
    def detect_chromium_version(self) -> Safe_Str__Version__Browser:
        version = self.chromium_version__from_driver_metadata()                     # Preferred — real browserVersion, e.g. "148.0.7778.96"
        if version is None:
            version = self.chromium_version__from_executable_path()                 # Fallback — digit token from an explicit executable path (build number at best)
        return Safe_Str__Version__Browser(version or FALLBACK_VERSION)

    def chromium_version__from_driver_metadata(self) -> str:                        # playwright/driver/package/browsers.json ships inside the pip package; its 'chromium' entry carries revision + browserVersion. It reports the version the PIP PACKAGE expects — which matches the baked browsers because the base image and the playwright pin move in lockstep (Dockerfile guard).
        try:
            import json
            import playwright
            from pathlib import Path
            browsers_file = Path(playwright.__file__).parent / 'driver' / 'package' / 'browsers.json'
            data          = json.loads(browsers_file.read_text())
            for browser in data.get('browsers', []):
                if browser.get('name') == 'chromium':
                    return browser.get('browserVersion') or None
        except Exception:                                                           # Health endpoints are hot — any surprise (missing file, bad JSON) degrades to the next fallback, never raises
            return None
        return None

    def chromium_version__from_executable_path(self) -> str:                        # Cheap path-segment parse only — no subprocess spawning in a health probe
        try:
            import os
            executable = get_env(ENV_VAR__CHROMIUM_EXECUTABLE)
            if executable and os.path.exists(executable):
                for segment in reversed(executable.split('/')):                     # e.g. .../chromium-1223/chrome-linux/chrome → '1223' (build number, not a Chrome version — metadata probe above is preferred)
                    digits = self.extract_version_digits(segment)
                    if digits != FALLBACK_VERSION:
                        return digits
        except Exception:
            return None
        return None

    def extract_version_digits(self, text: str) -> str:                             # Pulls 'chrome-1234' -> '1234' style tokens for Safe_Str__Version
        digits : List[str] = []
        current : str       = ''
        for ch in text:
            if ch.isdigit() or ch == '.':
                current += ch
            else:
                if current:
                    digits.append(current)
                current = ''
        if current:
            digits.append(current)
        return digits[-1] if digits else FALLBACK_VERSION

    def connectivity_check(self) -> Schema__Health__Check:                          # F1 — vault connectivity is a CAPABILITY (capabilities.has_vault_access), not liveness. gating=False keeps it visible in /health/status without flipping the aggregate: laptop / plain docker run deployments without SG_SEND_BASE_URL are still healthy.
        vault_url = get_env(ENV_VAR__SG_SEND_BASE_URL)
        return Schema__Health__Check(check_name = 'connectivity'                       ,
                                     healthy    = bool(vault_url)                     ,
                                     detail     = f'vault_url={vault_url}'            ,
                                     gating     = False                                )

# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Browser__Launcher
#
# Per-call Chromium lifecycle. Each call to launch() starts a fresh
# sync_playwright() Node subprocess AND a fresh Browser, so there is zero
# state bleed between requests (proxies, cookies, stuck handles, thread
# affinity). The Sequence__Runner / Playwright__Service call register()
# to associate the launch with a session_id, then stop(session_id) tears
# both down cleanly.
#
# Responsibilities:
#   • launch(browser_config) -> Schema__Browser__Launch__Result (browser + playwright + timings)
#   • register(session_id, result)                 — stash both handles per session
#   • stop(session_id)    -> browser_close_ms      — closes browser and stops playwright
#   • stop_all()                                    — shutdown hook (loops stop over every session)
#   • healthcheck()                                 — Schema__Health__Check
#
# Env var escape hatch:
#   SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE — absolute path to a Chromium binary.
#   Useful when (a) Playwright's default resolution points at a rev not
#   installed on disk (this sandbox), or (b) a laptop wants to use system
#   Chrome. When unset, Playwright picks its default.
#
# This class is the ONLY place allowed to import from playwright.sync_api
# outside of Step__Executor (spec §10). The rest of the service treats
# Browser/BrowserContext/sync_playwright objects as opaque.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import time
from typing                                                                                     import Any, Dict, List

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.utils.Env                                                                      import get_env

from sgraph_ai_service_playwright.consts.env_vars                                               import ENV_VAR__CHROMIUM_EXECUTABLE
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                       import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Launch__Result               import Schema__Browser__Launch__Result
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Name                             import Enum__Browser__Name
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Provider                         import Enum__Browser__Provider
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                     import Session_Id
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds            import Safe_UInt__Milliseconds
from sgraph_ai_service_playwright.schemas.service.Schema__Health__Check                         import Schema__Health__Check


DEFAULT_LAUNCH_ARGS : List[str] = ['--no-sandbox'           ,                        # Chromium sandbox needs privileges Lambda doesn't expose — without this, the subprocess dies instantly and subsequent new_page() raises TargetClosedError
                                   '--disable-gpu'          ,                        # No GPU in Lambda / most container runtimes
                                   '--disable-dev-shm-usage',                        # /dev/shm is tiny in Lambda containers — Chromium crashes on complex pages if it tries to use it
                                   '--single-process'       ,                        # Fits Lambda's single-vCPU model and avoids zombie helper processes
                                   '--use-mock-keychain'    ]                        # Skip macOS keychain integration on laptop targets — harmless elsewhere


class Browser__Launcher(Type_Safe):

    browsers : Dict[Session_Id, Schema__Browser__Launch__Result]                     # session_id → (browser, playwright, timings) — per-session clean state

    def launch(self, browser_config: Schema__Browser__Config) -> Schema__Browser__Launch__Result:
        self.assert_provider_supported(browser_config)
        self.assert_browser_supported (browser_config)

        from playwright.sync_api import sync_playwright                              # Local import keeps Type_Safe / cold-import surface small

        ts_before_pw       = self.now_ms()
        playwright         = sync_playwright().start()                               # Fresh Node subprocess per request — no cross-request handle reuse
        ts_after_pw        = self.now_ms()

        browser_type       = getattr(playwright, browser_config.browser_name.value)  # playwright.chromium / .firefox / .webkit
        launch_kwargs      = self.build_launch_kwargs(browser_config)
        ts_before_browser  = self.now_ms()
        browser            = browser_type.launch(**launch_kwargs)                    # Fresh Chromium process
        ts_after_browser   = self.now_ms()

        return Schema__Browser__Launch__Result(browser             = browser                                          ,
                                                playwright          = playwright                                       ,
                                                playwright_start_ms = Safe_UInt__Milliseconds(ts_after_pw      - ts_before_pw     ),
                                                browser_launch_ms   = Safe_UInt__Milliseconds(ts_after_browser - ts_before_browser))

    def register(self, session_id: Session_Id, result: Schema__Browser__Launch__Result) -> None:
        self.browsers[session_id] = result                                           # Both handles tracked together so stop() can close both

    def stop(self, session_id: Session_Id) -> Safe_UInt__Milliseconds:
        result = self.browsers.pop(session_id, None)
        if result is None:
            return Safe_UInt__Milliseconds(0)                                        # Idempotent — double-close is a no-op, not an error
        ts_before_close = self.now_ms()
        try:
            result.browser.close()
        except Exception:                                                            # Browser may already be dead; swallow — no useful recovery
            pass
        try:
            result.playwright.stop()                                                 # Kills the Node subprocess — matches the one we started in launch()
        except Exception:
            pass
        return Safe_UInt__Milliseconds(self.now_ms() - ts_before_close)

    def stop_all(self) -> None:
        for session_id in list(self.browsers.keys()):
            self.stop(session_id)

    # ─── helpers ───────────────────────────────────────────────────────────────

    def assert_provider_supported(self, browser_config: Schema__Browser__Config) -> None:
        if browser_config.provider != Enum__Browser__Provider.LOCAL_SUBPROCESS:
            raise NotImplementedError(f"Browser provider '{browser_config.provider.value}' not yet implemented; "
                                      f"only LOCAL_SUBPROCESS is supported today")

    def assert_browser_supported(self, browser_config: Schema__Browser__Config) -> None:
        if browser_config.browser_name != Enum__Browser__Name.CHROMIUM:
            raise NotImplementedError(f"Browser '{browser_config.browser_name.value}' not yet implemented; "
                                      f"only CHROMIUM is supported today")

    def build_launch_kwargs(self, browser_config: Schema__Browser__Config) -> Dict[str, Any]:
        kwargs : Dict[str, Any] = {'headless': bool(browser_config.headless)}

        exe = get_env(ENV_VAR__CHROMIUM_EXECUTABLE)                                  # Sandbox / laptop escape hatch
        if exe:
            kwargs['executable_path'] = exe

        args = [str(a) for a in (browser_config.launch_args or [])]                  # Caller's list, if any, REPLACES defaults (per spec §5.2)
        if not args:
            args = list(DEFAULT_LAUNCH_ARGS)                                         # Safe Chromium flags for Lambda + container runtimes
        kwargs['args'] = args

        if browser_config.proxy is not None:
            kwargs['proxy'] = self.build_proxy_dict(browser_config.proxy)

        return kwargs

    def build_proxy_dict(self, proxy) -> Dict[str, Any]:
        out : Dict[str, Any] = {'server': str(proxy.server)}
        if proxy.username: out['username'] = str(proxy.username)
        if proxy.password: out['password'] = str(proxy.password)
        bypass_hosts = [str(h) for h in (proxy.bypass or [])]
        if bypass_hosts:
            out['bypass'] = ','.join(bypass_hosts)
        return out

    def healthcheck(self) -> Schema__Health__Check:
        return Schema__Health__Check(check_name = 'browser_launcher'                                       ,
                                     healthy    = True                                                     ,
                                     detail     = f'active_browsers={len(self.browsers)}')                 # No more singleton playwright to report; every active browser has its own

    def active_session_ids(self) -> List[Session_Id]:
        return list(self.browsers.keys())

    def now_ms(self) -> int:                                                         # Single wall-clock seam — tests can subclass to freeze time
        return int(time.time() * 1000)

# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Browser__Launcher (v2 spec §4.8; v1 source not in pack)
#
# Chromium process lifecycle. Holds a single sync_playwright instance and a
# registry of {session_id: Browser} so `stop(session_id)` can shut down one
# session without disturbing others.
#
# Responsibilities:
#   • launch(browser_config)            -> Browser (Playwright object, opaque to rest of service)
#   • register(session_id, browser)     -> track per-session for later stop()
#   • stop(session_id)                  -> close that session's browser cleanly
#   • stop_all()                        -> shutdown hook
#   • healthcheck()                     -> Schema__Health__Check
#
# Env var escape hatch:
#   SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE — absolute path to a Chromium binary.
#   Useful when (a) Playwright's default resolution points at a rev not
#   installed on disk (this sandbox), or (b) a laptop wants to use system
#   Chrome. When unset, Playwright picks its default.
#
# This class is the ONLY place allowed to import from playwright.sync_api
# outside of Step__Executor (spec §10). The rest of the service treats
# Browser/BrowserContext objects as opaque (typed as `Any`).
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing                                                                                     import Any, Dict, List

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.utils.Env                                                                      import get_env

from sgraph_ai_service_playwright.consts.env_vars                                               import ENV_VAR__CHROMIUM_EXECUTABLE
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                       import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Name                             import Enum__Browser__Name
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Provider                         import Enum__Browser__Provider
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                     import Session_Id
from sgraph_ai_service_playwright.schemas.service.Schema__Health__Check                         import Schema__Health__Check


DEFAULT_LAUNCH_ARGS : List[str] = ['--no-sandbox'           ,                        # Chromium sandbox needs privileges Lambda doesn't expose — without this, the subprocess dies instantly and subsequent new_page() raises TargetClosedError
                                   '--disable-gpu'          ,                        # No GPU in Lambda / most container runtimes
                                   '--disable-dev-shm-usage',                        # /dev/shm is tiny in Lambda containers — Chromium crashes on complex pages if it tries to use it
                                   '--single-process'       ,                        # Fits Lambda's single-vCPU model and avoids zombie helper processes
                                   '--use-mock-keychain'    ]                        # Skip macOS keychain integration on laptop targets — harmless elsewhere


class Browser__Launcher(Type_Safe):

    playwright : Any            = None                                               # sync_playwright().start() handle — lazy
    browsers   : Dict[Session_Id, Any]                                               # session_id -> Playwright Browser

    def start(self) -> 'Browser__Launcher':                                          # Eager-init the sync_playwright runtime
        if self.playwright is None:
            from playwright.sync_api import sync_playwright
            self.playwright = sync_playwright().start()
        return self

    def launch(self, browser_config: Schema__Browser__Config) -> Any:
        self.start()
        self.assert_provider_supported(browser_config)
        self.assert_browser_supported (browser_config)

        browser_type = self.browser_type_for(browser_config.browser_name)
        launch_kwargs = self.build_launch_kwargs(browser_config)
        return browser_type.launch(**launch_kwargs)

    def register(self, session_id: Session_Id, browser: Any) -> None:
        self.browsers[session_id] = browser

    def stop(self, session_id: Session_Id) -> None:
        browser = self.browsers.pop(session_id, None)
        if browser is None:
            return
        try:
            browser.close()
        except Exception:                                                            # Browser may already be dead; swallow — no useful recovery at this layer
            pass

    def stop_all(self) -> None:
        for session_id in list(self.browsers.keys()):
            self.stop(session_id)
        if self.playwright is not None:
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None

    # ─── helpers ───────────────────────────────────────────────────────────────

    def assert_provider_supported(self, browser_config: Schema__Browser__Config) -> None:
        if browser_config.provider != Enum__Browser__Provider.LOCAL_SUBPROCESS:
            raise NotImplementedError(f"Browser provider '{browser_config.provider.value}' not yet implemented; "
                                      f"only LOCAL_SUBPROCESS is supported today")

    def assert_browser_supported(self, browser_config: Schema__Browser__Config) -> None:
        if browser_config.browser_name != Enum__Browser__Name.CHROMIUM:
            raise NotImplementedError(f"Browser '{browser_config.browser_name.value}' not yet implemented; "
                                      f"only CHROMIUM is supported today")

    def browser_type_for(self, browser_name: Enum__Browser__Name) -> Any:
        return getattr(self.playwright, browser_name.value)                          # playwright.chromium / .firefox / .webkit — names line up

    def build_launch_kwargs(self, browser_config: Schema__Browser__Config) -> Dict[str, Any]:
        kwargs : Dict[str, Any] = {'headless': bool(browser_config.headless)}

        exe = get_env(ENV_VAR__CHROMIUM_EXECUTABLE)                                  # Sandbox / laptop escape hatch
        if exe:
            kwargs['executable_path'] = exe

        args = [str(a) for a in (browser_config.launch_args or [])]                  # Caller's list, if any, REPLACES defaults (per spec §5.2 — "caller's list replaces defaults entirely")
        if not args:
            args = list(DEFAULT_LAUNCH_ARGS)                                         # No caller list → fall back to spec-mandated defaults; without these Chromium dies on Lambda (--no-sandbox) and gets OOM-killed on /dev/shm (--disable-dev-shm-usage)
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
        started = self.playwright is not None
        return Schema__Health__Check(check_name = 'browser_launcher'                                       ,
                                     healthy    = True                                                     ,
                                     detail     = f'playwright_started={started} active_browsers={len(self.browsers)}')

    def active_session_ids(self) -> List[Session_Id]:
        return list(self.browsers.keys())

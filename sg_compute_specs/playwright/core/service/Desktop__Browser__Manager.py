# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Desktop__Browser__Manager
#
# Opens long-lived HEADED browsers on the container's X display for the
# sg-playwright-vnc image (display_mode=vnc): the browser window renders on Xvfb
# :99 and is visible/drivable in noVNC (:6080). Pure composition over the
# existing session machinery — session_open launches (headed) and session_act
# navigates via a NAVIGATE step, so no page.* call is made here (rule §16:
# Step__Executor only) and the returned session_id works with every
# /session/{id}/* endpoint. That shared session_id IS the hybrid feature:
# automation acts on the same browser the human watches.
#
# display_mode guard: on a headless instance (base image — no X server) a headed
# launch would die with an obscure Playwright error; reject up-front with a 400
# that names the env var instead.
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                                        import HTTPException
from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.utils.Env                                                                          import get_env

from sg_compute_specs.playwright.core.consts.env_vars                                                   import ENV_VAR__DISPLAY_MODE
from sg_compute_specs.playwright.core.schemas.browser.Schema__Browser__Config                            import Schema__Browser__Config
from sg_compute_specs.playwright.core.schemas.desktop.Schema__Desktop__Browser__Request                  import Schema__Desktop__Browser__Request
from sg_compute_specs.playwright.core.schemas.desktop.Schema__Desktop__Browser__Response                 import Schema__Desktop__Browser__Response
from sg_compute_specs.playwright.core.schemas.enums.Enum__Display__Mode                                  import Enum__Display__Mode
from sg_compute_specs.playwright.core.schemas.enums.Enum__Sequence__Status                               import Enum__Sequence__Status
from sg_compute_specs.playwright.core.schemas.session_handle.Schema__Session__Act__Request               import Schema__Session__Act__Request
from sg_compute_specs.playwright.core.schemas.session_handle.Schema__Session__Open__Request              import Schema__Session__Open__Request
from sg_compute_specs.playwright.core.service.Playwright__Service                                        import Playwright__Service


def display_mode() -> Enum__Display__Mode:                                          # env-driven; unknown/absent values mean headless (the safe base-image default)
    raw = str(get_env(ENV_VAR__DISPLAY_MODE) or '').strip().lower()
    if raw == Enum__Display__Mode.VNC.value:
        return Enum__Display__Mode.VNC
    return Enum__Display__Mode.HEADLESS


class Desktop__Browser__Manager(Type_Safe):
    service : Playwright__Service

    def open_browser(self, request: Schema__Desktop__Browser__Request) -> Schema__Desktop__Browser__Response:
        if display_mode() != Enum__Display__Mode.VNC:
            raise HTTPException(400, f'/desktop/browser needs {ENV_VAR__DISPLAY_MODE}=vnc — this instance is '
                                     f'headless (no X display to render a headed browser on)')
        browser_config = Schema__Browser__Config(browser_name = request.engine,
                                                 headless     = False         )      # Browser__Launcher picks the headed default args (no --single-process)
        open_request   = Schema__Session__Open__Request(browser_config = browser_config,
                                                        ttl_ms         = request.ttl_ms)
        opened         = self.service.session_open(open_request)

        navigated = False
        start_url = str(request.start_url or '')
        if start_url:                                                                # navigate ON the session worker thread via the normal step pipeline
            act    = Schema__Session__Act__Request(steps=[{'action': 'navigate', 'url': start_url}])
            result = self.service.session_act(str(opened.session_id), act)
            navigated = getattr(result, 'status', None) == Enum__Sequence__Status.COMPLETED

        return Schema__Desktop__Browser__Response(session_id    = opened.session_id            ,
                                                  engine        = request.engine               ,
                                                  start_url     = request.start_url            ,
                                                  navigated     = navigated                    ,
                                                  expires_at_ms = int(opened.expires_at_ms or 0))

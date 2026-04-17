# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Session__Manager (v2 spec §4; behaviour derived from
# callsites in routes-catalogue-v2.md — full v1 source not in dev pack)
#
# In-memory registry for session lifecycle. Owns:
#   • Schema__Session__Info records                (sessions        )
#   • Live Playwright Browser objects              (browsers        )
#   • Per-session Schema__Capture__Config defaults (capture_configs)
#   • Per-session start wall-clock (ms epoch)      (start_times     )
#   • Per-session accumulated artefact refs        (artefacts       )
#
# No Playwright calls live here — Browser objects are opaque. Actual `page.*`
# work belongs to Step__Executor; browser launch/stop belongs to Browser__Launcher.
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing                                                                                         import Any, Dict, List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now                    import Timestamp_Now

from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.collections.Dict__Session__Browsers__By_Id                import Dict__Session__Browsers__By_Id
from sgraph_ai_service_playwright.schemas.collections.Dict__Sessions__By_Id                         import Dict__Sessions__By_Id
from sgraph_ai_service_playwright.schemas.collections.List__Artefact__Refs                          import List__Artefact__Refs
from sgraph_ai_service_playwright.schemas.enums.Enum__Session__Status                               import Enum__Session__Status
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                         import Session_Id
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sgraph_ai_service_playwright.schemas.service.Schema__Health__Check                             import Schema__Health__Check
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities                     import Schema__Service__Capabilities
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Request                  import Schema__Session__Create__Request
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Info                             import Schema__Session__Info


class Session__Manager(Type_Safe):

    sessions         : Dict__Sessions__By_Id
    browsers         : Dict__Session__Browsers__By_Id
    capture_configs  : Dict[Session_Id, Schema__Capture__Config]
    start_times      : Dict[Session_Id, int]                                        # Wall-clock ms epoch at create()
    artefacts        : Dict[Session_Id, List__Artefact__Refs]

    def create(self                                                 ,
               browser      : Any                                   ,                # Opaque Playwright Browser
               request      : Schema__Session__Create__Request      ,
               trace_id     : Any                                   ,                # Safe_Str__Trace_Id
               capabilities : Schema__Service__Capabilities
          ) -> Schema__Session__Info:

        session_id = Session_Id()                                                   # Auto-generated unique handle
        now_ms     = self.now_ms()
        lifetime   = min(int(request.lifetime_ms), int(capabilities.max_session_lifetime_ms))

        session = Schema__Session__Info(session_id         = session_id                              ,
                                        status             = Enum__Session__Status.ACTIVE            ,
                                        created_at         = Timestamp_Now(now_ms)                   ,
                                        last_activity_at   = Timestamp_Now(now_ms)                   ,
                                        expires_at         = Timestamp_Now(now_ms + lifetime)        ,
                                        trace_id           = trace_id                                ,
                                        browser_name       = request.browser_config.browser_name     ,
                                        total_actions      = Safe_UInt(0)                            ,
                                        artefacts_captured = Safe_UInt(0)                            )

        self.sessions       [session_id] = session
        self.browsers       [session_id] = browser
        self.capture_configs[session_id] = request.capture_config
        self.start_times    [session_id] = now_ms
        self.artefacts      [session_id] = List__Artefact__Refs()
        return session

    def get(self, session_id: Session_Id) -> Schema__Session__Info:
        return self.sessions.get(session_id)

    def get_browser(self, session_id: Session_Id) -> Any:
        return self.browsers.get(session_id)

    def get_capture_config(self, session_id: Session_Id) -> Schema__Capture__Config:
        return self.capture_configs.get(session_id)

    def get_start_time(self, session_id: Session_Id) -> int:
        return self.start_times.get(session_id, self.now_ms())

    def get_artefacts(self, session_id: Session_Id) -> List__Artefact__Refs:
        return self.artefacts.get(session_id, List__Artefact__Refs())

    def list_active(self) -> List[Schema__Session__Info]:
        return [s for s in self.sessions.values()
                if s.status in (Enum__Session__Status.ACTIVE, Enum__Session__Status.IDLE)]

    def record_action(self                                          ,
                      session_id  : Session_Id                      ,
                      step_result : Schema__Step__Result__Base
                 ) -> None:

        session = self.sessions.get(session_id)
        if session is None:
            return

        session.last_activity_at   = Timestamp_Now(self.now_ms())
        session.total_actions      = Safe_UInt(int(session.total_actions) + 1)
        session.artefacts_captured = Safe_UInt(int(session.artefacts_captured) + len(step_result.artefacts))

        bucket = self.artefacts.setdefault(session_id, List__Artefact__Refs())
        for ref in step_result.artefacts:
            bucket.append(ref)

    def add_artefact(self, session_id: Session_Id, ref: Schema__Artefact__Ref) -> None:
        if session_id not in self.sessions:
            return                                                                  # Drop ref silently — caller bug if session is gone
        bucket = self.artefacts.setdefault(session_id, List__Artefact__Refs())
        bucket.append(ref)
        session = self.sessions[session_id]
        session.artefacts_captured = Safe_UInt(int(session.artefacts_captured) + 1)

    def close(self, session_id: Session_Id) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            return
        session.status = Enum__Session__Status.CLOSED
        self.browsers.pop(session_id, None)                                         # Drop live Browser ref — actual .close() lives in Browser__Launcher

    def healthcheck(self) -> Schema__Health__Check:
        active = len(self.list_active())
        return Schema__Health__Check(check_name = 'session_manager'                   ,
                                     healthy    = True                                ,
                                     detail     = f'active_sessions={active}'          )

    def now_ms(self) -> int:                                                        # Single wall-clock seam (tests can subclass to freeze time)
        return int(time.time() * 1000)

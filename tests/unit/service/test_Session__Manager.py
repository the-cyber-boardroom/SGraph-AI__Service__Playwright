# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Session__Manager (derived shape from routes-catalogue-v2 §4 callsites)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Ref          import Schema__Artefact__Ref
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config         import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink              import Enum__Artefact__Sink
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Type              import Enum__Artefact__Type
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Name               import Enum__Browser__Name
from sgraph_ai_service_playwright.schemas.enums.Enum__Session__Status             import Enum__Session__Status
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Action                import Enum__Step__Action
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Status                import Enum__Step__Status
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id       import Session_Id
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base      import Schema__Step__Result__Base
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities   import Schema__Service__Capabilities
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Request import Schema__Session__Create__Request
from sgraph_ai_service_playwright.service.Session__Manager                         import Session__Manager


def _caps(max_lifetime_ms: int = 900_000) -> Schema__Service__Capabilities:
    return Schema__Service__Capabilities(supports_persistent     = False                                  ,
                                         supports_video          = True                                   ,
                                         max_session_lifetime_ms = max_lifetime_ms                        ,
                                         available_browsers      = [Enum__Browser__Name.CHROMIUM]         ,
                                         supported_sinks         = [Enum__Artefact__Sink.INLINE]          ,
                                         memory_budget_mb        = 1024                                   ,
                                         has_vault_access        = False                                  ,
                                         has_s3_access           = False                                  ,
                                         has_network_egress      = True                                   ,
                                         proxy_configured        = False                                  )


def _request(lifetime_ms: int = 60_000) -> Schema__Session__Create__Request:
    return Schema__Session__Create__Request(lifetime_ms = lifetime_ms)


def _step_result(artefacts=None, action=Enum__Step__Action.NAVIGATE) -> Schema__Step__Result__Base:
    return Schema__Step__Result__Base(action      = action                   ,
                                      status      = Enum__Step__Status.PASSED ,
                                      duration_ms = 10                        ,
                                      artefacts   = artefacts or []           )


class _FrozenSessionManager(Session__Manager):                                      # Deterministic clock for assertions on timestamps
    fixed_now : int = 1_700_000_000_000                                             # 2023-11-14 ~22:13 UTC
    def now_ms(self) -> int:
        return self.fixed_now


class test_create(TestCase):

    def test__create_stores_session_browser_config_and_start_time(self):
        sm = _FrozenSessionManager()
        browser = object()
        session = sm.create(browser=browser, request=_request(), trace_id=Safe_Str__Trace_Id('t1'), capabilities=_caps())
        assert session.status                               == Enum__Session__Status.ACTIVE
        assert sm.get        (session.session_id)           is session
        assert sm.get_browser(session.session_id)           is browser
        assert sm.get_start_time(session.session_id)        == sm.fixed_now
        assert sm.get_capture_config(session.session_id)    is not None
        assert int(session.created_at)                      == sm.fixed_now
        assert int(session.expires_at)                      == sm.fixed_now + 60_000

    def test__expires_at_capped_by_capabilities(self):                              # max_session_lifetime_ms caps the request
        sm = _FrozenSessionManager()
        session = sm.create(browser=object(), request=_request(lifetime_ms=10_000_000),
                            trace_id=Safe_Str__Trace_Id('t2'), capabilities=_caps(max_lifetime_ms=900_000))
        assert int(session.expires_at) - int(session.created_at) == 900_000

    def test__session_ids_are_unique_across_creates(self):
        sm = Session__Manager()
        s1 = sm.create(browser=object(), request=_request(), trace_id=Safe_Str__Trace_Id('t1'), capabilities=_caps())
        s2 = sm.create(browser=object(), request=_request(), trace_id=Safe_Str__Trace_Id('t1'), capabilities=_caps())
        assert s1.session_id != s2.session_id

    def test__browser_name_copied_from_request_config(self):
        sm = Session__Manager()
        req = Schema__Session__Create__Request()
        req.browser_config.browser_name = Enum__Browser__Name.FIREFOX
        session = sm.create(browser=object(), request=req, trace_id=Safe_Str__Trace_Id('t'), capabilities=_caps())
        assert session.browser_name == Enum__Browser__Name.FIREFOX


class test_accessors(TestCase):

    def test__get_returns_none_for_unknown(self):
        sm = Session__Manager()
        assert sm.get(Session_Id('nope')) is None

    def test__get_browser_returns_none_for_unknown(self):
        sm = Session__Manager()
        assert sm.get_browser(Session_Id('nope')) is None

    def test__get_artefacts_returns_empty_for_unknown(self):                        # Callers expect an iterable, not None
        sm = Session__Manager()
        out = sm.get_artefacts(Session_Id('nope'))
        assert list(out) == []

    def test__get_capture_config_returns_stored_config(self):
        sm = Session__Manager()
        req = _request()
        session = sm.create(browser=object(), request=req, trace_id=Safe_Str__Trace_Id('t'), capabilities=_caps())
        assert sm.get_capture_config(session.session_id) is req.capture_config


class test_list_active(TestCase):

    def test__includes_active_and_idle_but_not_closed(self):
        sm = Session__Manager()
        s_active = sm.create(browser=object(), request=_request(), trace_id=Safe_Str__Trace_Id('ta'), capabilities=_caps())
        s_idle   = sm.create(browser=object(), request=_request(), trace_id=Safe_Str__Trace_Id('ti'), capabilities=_caps())
        s_closed = sm.create(browser=object(), request=_request(), trace_id=Safe_Str__Trace_Id('tc'), capabilities=_caps())

        sm.sessions[s_idle.session_id].status = Enum__Session__Status.IDLE
        sm.close(s_closed.session_id)

        ids = {s.session_id for s in sm.list_active()}
        assert s_active.session_id in ids
        assert s_idle  .session_id in ids
        assert s_closed.session_id not in ids


class test_record_action(TestCase):

    def test__updates_counters_and_last_activity(self):
        sm = _FrozenSessionManager()
        session = sm.create(browser=object(), request=_request(), trace_id=Safe_Str__Trace_Id('t'), capabilities=_caps())

        sm.fixed_now += 1_000                                                       # Fake a 1-second jump before the action
        artefact = Schema__Artefact__Ref(artefact_type = Enum__Artefact__Type.SCREENSHOT,
                                         sink          = Enum__Artefact__Sink.INLINE    )
        sm.record_action(session.session_id, _step_result(artefacts=[artefact]))

        refreshed = sm.get(session.session_id)
        assert int(refreshed.total_actions)      == 1
        assert int(refreshed.artefacts_captured) == 1
        assert int(refreshed.last_activity_at)   == sm.fixed_now                    # Bumped forward
        assert list(sm.get_artefacts(session.session_id))[0].artefact_type == Enum__Artefact__Type.SCREENSHOT

    def test__is_noop_for_unknown_session(self):                                    # Must not raise; must not record anything
        sm = Session__Manager()
        sm.record_action(Session_Id('ghost'), _step_result())                       # No raise
        assert list(sm.get_artefacts(Session_Id('ghost'))) == []


class test_add_artefact(TestCase):

    def test__appends_and_bumps_count(self):
        sm = Session__Manager()
        session = sm.create(browser=object(), request=_request(), trace_id=Safe_Str__Trace_Id('t'), capabilities=_caps())
        ref = Schema__Artefact__Ref(artefact_type=Enum__Artefact__Type.VIDEO, sink=Enum__Artefact__Sink.INLINE)
        sm.add_artefact(session.session_id, ref)
        assert len(list(sm.get_artefacts(session.session_id))) == 1
        assert int(sm.get(session.session_id).artefacts_captured) == 1

    def test__drops_for_unknown_session(self):                                      # Late-arriving artefact refs after close are ignored
        sm = Session__Manager()
        ref = Schema__Artefact__Ref(artefact_type=Enum__Artefact__Type.VIDEO, sink=Enum__Artefact__Sink.INLINE)
        sm.add_artefact(Session_Id('ghost'), ref)
        assert list(sm.get_artefacts(Session_Id('ghost'))) == []


class test_close(TestCase):

    def test__marks_session_closed_and_drops_browser(self):
        sm = Session__Manager()
        session = sm.create(browser=object(), request=_request(), trace_id=Safe_Str__Trace_Id('t'), capabilities=_caps())
        sm.close(session.session_id)
        assert sm.get(session.session_id).status is Enum__Session__Status.CLOSED
        assert sm.get_browser(session.session_id) is None                            # Browser ref dropped; Browser__Launcher handles .close()

    def test__close_is_idempotent(self):
        sm = Session__Manager()
        session = sm.create(browser=object(), request=_request(), trace_id=Safe_Str__Trace_Id('t'), capabilities=_caps())
        sm.close(session.session_id)
        sm.close(session.session_id)                                                # Second close must not raise
        assert sm.get(session.session_id).status is Enum__Session__Status.CLOSED

    def test__close_unknown_is_noop(self):
        sm = Session__Manager()
        sm.close(Session_Id('ghost'))                                               # Must not raise


class test_healthcheck(TestCase):

    def test__reports_active_count(self):
        sm = Session__Manager()
        sm.create(browser=object(), request=_request(), trace_id=Safe_Str__Trace_Id('t1'), capabilities=_caps())
        sm.create(browser=object(), request=_request(), trace_id=Safe_Str__Trace_Id('t2'), capabilities=_caps())
        hc = sm.healthcheck()
        assert hc.check_name == 'session_manager'
        assert hc.healthy    is True
        assert 'active_sessions=2' in str(hc.detail)

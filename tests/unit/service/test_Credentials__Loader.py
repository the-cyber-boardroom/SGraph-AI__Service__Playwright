# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Credentials__Loader (vault ↔ browser-context glue)
#
# Uses lightweight fake Browser / BrowserContext classes that record the calls
# made to them. No mocks, no patches. The Artefact__Writer seams are replaced
# with the same in-memory subclass pattern used in test_Artefact__Writer.py.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                import Any, Dict, List, Tuple
from unittest                                                                              import TestCase

from sgraph_ai_service_playwright.schemas.artefact.Schema__Vault_Ref                       import Schema__Vault_Ref
from sgraph_ai_service_playwright.schemas.enums.Enum__Artefact__Sink                       import Enum__Artefact__Sink
from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Name                        import Enum__Browser__Name
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id        import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                import Session_Id
from sgraph_ai_service_playwright.schemas.primitives.vault.Safe_Str__Vault_Key             import Safe_Str__Vault_Key
from sgraph_ai_service_playwright.schemas.primitives.vault.Safe_Str__Vault_Path            import Safe_Str__Vault_Path
from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities            import Schema__Service__Capabilities
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Request         import Schema__Session__Create__Request
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Credentials             import Schema__Session__Credentials
from sgraph_ai_service_playwright.service.Artefact__Writer                                  import Artefact__Writer
from sgraph_ai_service_playwright.service.Credentials__Loader                               import Credentials__Loader
from sgraph_ai_service_playwright.service.Session__Manager                                  import Session__Manager


class _FakeContext:                                                                # Minimal recorder; matches the subset of Playwright BrowserContext the loader touches
    def __init__(self):
        self.added_cookies : List[list] = []
        self.headers       : Dict[str, str] = None

    def add_cookies(self, cookies):
        self.added_cookies.append(cookies)

    def set_extra_http_headers(self, headers: Dict[str, str]):
        self.headers = dict(headers)


class _FakeBrowser:
    def __init__(self, context=None):
        self._contexts = [context if context is not None else _FakeContext()]

    @property                                                                                # Real Playwright sync API exposes `contexts` as a property
    def contexts(self):
        return self._contexts


class _InMemoryWriter(Artefact__Writer):                                           # Vault seams backed by a dict — same pattern as test_Artefact__Writer
    store : Dict[Tuple[str, str], Any] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.store = {}

    def read_from_vault(self, vault_ref):
        return self.store.get((str(vault_ref.vault_key), str(vault_ref.path)))

    def write_to_vault(self, vault_ref, data):
        self.store[(str(vault_ref.vault_key), str(vault_ref.path))] = data


def _caps() -> Schema__Service__Capabilities:
    return Schema__Service__Capabilities(supports_persistent     = False                                 ,
                                         supports_video          = True                                  ,
                                         max_session_lifetime_ms = 900_000                               ,
                                         available_browsers      = [Enum__Browser__Name.CHROMIUM]        ,
                                         supported_sinks         = [Enum__Artefact__Sink.INLINE]         ,
                                         memory_budget_mb        = 1024                                  ,
                                         has_vault_access        = True                                  ,
                                         has_s3_access           = False                                 ,
                                         has_network_egress      = True                                  ,
                                         proxy_configured        = False                                 )


def _create_session(sm: Session__Manager, browser) -> Session_Id:
    info = sm.create(browser      = browser                                              ,
                     request      = Schema__Session__Create__Request(lifetime_ms=60_000) ,
                     trace_id     = Safe_Str__Trace_Id('t1')                             ,
                     capabilities = _caps()                                              )
    return info.session_id


def _ref(path: str = '/creds/cookies.json') -> Schema__Vault_Ref:
    return Schema__Vault_Ref(vault_key = Safe_Str__Vault_Key('test-vault') ,
                             path      = Safe_Str__Vault_Path(path)        )


class test_apply__cookies(TestCase):

    def test__loads_cookies_from_vault_and_adds_to_context(self):
        writer = _InMemoryWriter()
        ctx    = _FakeContext()
        sm     = Session__Manager()
        sid    = _create_session(sm, _FakeBrowser(ctx))
        cookies = [{'name': 'sid', 'value': 'abc', 'domain': 'example.com'}]
        writer.write_to_vault(_ref(), cookies)                                     # Seed the "vault"

        loader = Credentials__Loader(artefact_writer=writer)
        loader.apply(sid, sm, Schema__Session__Credentials(cookies_vault_ref=_ref()))

        assert ctx.added_cookies == [cookies]
        assert ctx.headers is None                                                 # No headers asked for

    def test__empty_vault_payload_is_skipped(self):                                # read_from_vault returning None/[] must not trigger add_cookies
        writer = _InMemoryWriter()
        ctx    = _FakeContext()
        sm     = Session__Manager()
        sid    = _create_session(sm, _FakeBrowser(ctx))

        loader = Credentials__Loader(artefact_writer=writer)
        loader.apply(sid, sm, Schema__Session__Credentials(cookies_vault_ref=_ref()))

        assert ctx.added_cookies == []                                             # Nothing in vault → no call


class test_apply__storage_state(TestCase):

    def test__extracts_cookies_from_state_payload(self):
        writer = _InMemoryWriter()
        ctx    = _FakeContext()
        sm     = Session__Manager()
        sid    = _create_session(sm, _FakeBrowser(ctx))
        state  = {'cookies': [{'name': 'sid', 'value': 'xyz'}], 'origins': []}
        ref    = _ref('/creds/state.json')
        writer.write_to_vault(ref, state)

        loader = Credentials__Loader(artefact_writer=writer)
        loader.apply(sid, sm, Schema__Session__Credentials(storage_state_vault_ref=ref))

        assert ctx.added_cookies == [state['cookies']]

    def test__state_without_cookies_key_is_skipped(self):
        writer = _InMemoryWriter()
        ctx    = _FakeContext()
        sm     = Session__Manager()
        sid    = _create_session(sm, _FakeBrowser(ctx))
        ref    = _ref('/creds/state.json')
        writer.write_to_vault(ref, {'origins': []})                                # No 'cookies' key

        loader = Credentials__Loader(artefact_writer=writer)
        loader.apply(sid, sm, Schema__Session__Credentials(storage_state_vault_ref=ref))

        assert ctx.added_cookies == []


class test_apply__headers(TestCase):

    def test__sets_extra_http_headers_when_provided(self):
        writer = _InMemoryWriter()
        ctx    = _FakeContext()
        sm     = Session__Manager()
        sid    = _create_session(sm, _FakeBrowser(ctx))

        creds = Schema__Session__Credentials(extra_http_headers={'Authorization': 'Bearer abc',
                                                                 'X-Trace-Id'   : 'req-123'   })
        loader = Credentials__Loader(artefact_writer=writer)
        loader.apply(sid, sm, creds)

        assert ctx.headers == {'authorization': 'Bearer abc',                       # Safe_Str__Http__Header__Name normalises to lowercase
                               'x-trace-id'   : 'req-123'  }

    def test__empty_headers_dict_does_not_call_set(self):                          # Schema default is an empty dict; apply() should no-op
        writer = _InMemoryWriter()
        ctx    = _FakeContext()
        sm     = Session__Manager()
        sid    = _create_session(sm, _FakeBrowser(ctx))

        loader = Credentials__Loader(artefact_writer=writer)
        loader.apply(sid, sm, Schema__Session__Credentials())

        assert ctx.headers is None


class test_apply__missing_browser(TestCase):

    def test__unknown_session_is_silent_noop(self):                                # Caller error, not a 500 — just return
        writer = _InMemoryWriter()
        sm     = Session__Manager()
        loader = Credentials__Loader(artefact_writer=writer)

        loader.apply(Session_Id(), sm,
                     Schema__Session__Credentials(cookies_vault_ref=_ref()))       # No exception


class test_apply__combined(TestCase):

    def test__cookies_state_and_headers_all_applied_in_order(self):
        writer = _InMemoryWriter()
        ctx    = _FakeContext()
        sm     = Session__Manager()
        sid    = _create_session(sm, _FakeBrowser(ctx))

        cookies_ref = _ref('/creds/cookies.json')
        state_ref   = _ref('/creds/state.json'  )
        writer.write_to_vault(cookies_ref, [{'name': 'a', 'value': '1'}])
        writer.write_to_vault(state_ref  , {'cookies': [{'name': 'b', 'value': '2'}]})

        creds  = Schema__Session__Credentials(cookies_vault_ref       = cookies_ref                          ,
                                              storage_state_vault_ref = state_ref                            ,
                                              extra_http_headers      = {'X-Env': 'test'}                    )
        loader = Credentials__Loader(artefact_writer=writer)
        loader.apply(sid, sm, creds)

        assert ctx.added_cookies == [[{'name': 'a', 'value': '1'}],                 # cookies first
                                     [{'name': 'b', 'value': '2'}]]                 # then state.cookies
        assert ctx.headers == {'x-env': 'test'}                                     # Header names are normalised to lowercase by the safe_str primitive


class test_save_state_to_vault(TestCase):

    def test__delegates_to_artefact_writer_write_to_vault(self):
        writer = _InMemoryWriter()
        loader = Credentials__Loader(artefact_writer=writer)
        state  = {'cookies': [{'name': 'sid', 'value': 'persist-me'}]}
        ref    = _ref('/creds/state.json')

        loader.save_state_to_vault(ref, state)

        assert writer.store[('test-vault', '/creds/state.json')] == state

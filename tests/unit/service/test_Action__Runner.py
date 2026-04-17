# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Action__Runner (Layer-0 single-action execution)
#
# Drives Action__Runner through a fully wired Playwright__Service (setup()
# shares session_manager / capability_detector / request_validator across
# both objects). Real Chromium is NOT launched — the Browser__Launcher is
# swapped with a fake that returns opaque _FakeBrowser / _FakeContext /
# _FakePage stand-ins. Step__Executor runs for real against those fakes, so
# these tests also exercise the Step__Executor NAVIGATE / CLICK / SCREENSHOT
# handlers end-to-end through Action__Runner's glue.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import pytest
from typing                                                                                 import Any
from unittest                                                                               import TestCase

from fastapi                                                                                import HTTPException

from sgraph_ai_service_playwright.consts.env_vars                                           import (ENV_VAR__AWS_LAMBDA_RUNTIME_API,
                                                                                                    ENV_VAR__CI                    ,
                                                                                                    ENV_VAR__CLAUDE_SESSION        ,
                                                                                                    ENV_VAR__DEPLOYMENT_TARGET     ,
                                                                                                    ENV_VAR__SG_SEND_BASE_URL      )
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                   import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Launch__Result            import Schema__Browser__Launch__Result
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                   import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.core.Schema__Action__Request                      import Schema__Action__Request
from sgraph_ai_service_playwright.schemas.enums.Enum__Step__Status                           import Enum__Step__Status
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Create__Request          import Schema__Session__Create__Request
from sgraph_ai_service_playwright.service.Artefact__Writer                                  import Artefact__Writer
from sgraph_ai_service_playwright.service.Browser__Launcher                                 import Browser__Launcher
from sgraph_ai_service_playwright.service.Credentials__Loader                               import Credentials__Loader
from sgraph_ai_service_playwright.service.Playwright__Service                               import Playwright__Service


ENV_KEYS = [ENV_VAR__AWS_LAMBDA_RUNTIME_API,
            ENV_VAR__CI                    ,
            ENV_VAR__CLAUDE_SESSION        ,
            ENV_VAR__DEPLOYMENT_TARGET     ,
            ENV_VAR__SG_SEND_BASE_URL      ]


class _EnvScrub:                                                                     # Freeze capability detection to a known target
    def __init__(self, **overrides):
        self.overrides = dict(overrides)
        self.snapshot  = {}
    def __enter__(self):
        for k in ENV_KEYS:
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self
    def __exit__(self, *exc):
        for k in ENV_KEYS:
            os.environ.pop(k, None)
            if self.snapshot.get(k) is not None:
                os.environ[k] = self.snapshot[k]


# ─── Fakes (no real Chromium) ────────────────────────────────────────────────

class _FakeLocator:                                                                  # Stand-in for page.locator(selector) — used by fill(clear_first=False), get_content(with selector), screenshot(with selector)
    def __init__(self, selector):
        self.selector       = selector
        self.type_sequences = []
    def press_sequentially(self, value, timeout=None):
        self.type_sequences.append({'value': value, 'timeout': timeout})
    def inner_text(self, timeout=None): return f'text-for:{self.selector}'
    def inner_html(self, timeout=None): return f'<span>html-for:{self.selector}</span>'
    def screenshot(self, timeout=None): return b'\x89PNG\r\n\x1a\n' + b'\x00' * 16


class _FakePage:                                                                     # Playwright Page stand-in — records every call Step__Executor makes
    def __init__(self):
        self.goto_calls       = []
        self.click_calls      = []
        self.fill_calls       = []
        self.screenshot_calls = []
        self.content_calls    = 0
        self.locators         = []
        self.url              = 'http://example.com/current'
    def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls.append({'url': url, 'wait_until': wait_until, 'timeout': timeout})
        self.url = url
    def click(self, selector, button=None, click_count=None, delay=None, force=None, timeout=None):
        self.click_calls.append({'selector': selector, 'button': button, 'click_count': click_count,
                                  'delay': delay, 'force': force, 'timeout': timeout})
    def fill(self, selector, value, timeout=None):
        self.fill_calls.append({'selector': selector, 'value': value, 'timeout': timeout})
    def screenshot(self, full_page=False, timeout=None):
        call = {'full_page': full_page, 'timeout': timeout}
        self.screenshot_calls.append(call)
        return b'\x89PNG\r\n\x1a\n' + b'\x00' * 16                                    # Looks-like-PNG bytes; size doesn't matter for these tests
    def content(self):
        self.content_calls += 1
        return '<html><body>full-page-html</body></html>'
    def locator(self, selector):
        locator = _FakeLocator(selector)
        self.locators.append(locator)
        return locator


class _FakeContext:                                                                  # Playwright BrowserContext stand-in
    def __init__(self):
        self.pages = []
    def new_page(self):
        page = _FakePage()
        self.pages.append(page)
        return page
    def storage_state(self):
        return {'cookies': [], 'origins': []}
    def add_cookies(self, cookies): pass
    def set_extra_http_headers(self, headers): pass


class _FakeBrowser:                                                                  # Playwright Browser stand-in
    def __init__(self):
        self._contexts = []
    @property                                                                       # Real Playwright sync API: `contexts` is a @property (not a method)
    def contexts(self):
        return self._contexts
    def new_context(self):
        context = _FakeContext()
        self._contexts.append(context)
        return context
    def close(self): pass


class _FakePlaywright:                                                               # sync_playwright() stand-in — only needs a stop() no-op
    def stop(self): pass


class _FakeLauncher(Browser__Launcher):                                              # Subclass Browser__Launcher — satisfies Type_Safe attribute type
    def launch(self, browser_config):
        return Schema__Browser__Launch__Result(browser             = _FakeBrowser()  ,     # Real launcher returns Schema__Browser__Launch__Result now — wrap the fake in the same shape
                                                playwright          = _FakePlaywright(),
                                                playwright_start_ms = 0                ,
                                                browser_launch_ms   = 0                )
    def stop(self, session_id):
        return 0                                                                     # Sequence__Runner converts this to Safe_UInt__Milliseconds for timings.browser_close_ms


class _InMemoryArtefactWriter(Artefact__Writer):                                     # Not used by NAVIGATE / CLICK; SCREENSHOT's sink is disabled by default
    def read_from_vault(self, vault_ref): return None
    def write_to_vault (self, vault_ref, data): pass


def _build_service():
    writer   = _InMemoryArtefactWriter()
    launcher = _FakeLauncher()
    service  = Playwright__Service(browser_launcher   = launcher                                  ,
                                   credentials_loader = Credentials__Loader(artefact_writer=writer))
    return service.setup()                                                           # Wire Action__Runner's shared deps


def _open_session(service: Playwright__Service):                                     # Create one active session, return its id
    request  = Schema__Session__Create__Request(browser_config = Schema__Browser__Config(),
                                                capture_config = Schema__Capture__Config())
    response = service.session_create(request)
    return response.session_info.session_id


class test_execute__navigate(TestCase):

    def test__returns_response_with_passed_step_result(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            request    = Schema__Action__Request(session_id = session_id                                                     ,
                                                  step       = {'action': 'navigate', 'url': 'http://example.com/'}          )
            response   = service.execute_action(request)

        assert response.session_id              == session_id
        assert response.step_result.status      == Enum__Step__Status.PASSED
        assert str(response.step_result.action) == 'navigate'
        assert response.session_info.total_actions == 1

    def test__creates_context_and_page_lazily_on_first_navigate(self):                # Fresh browser has no contexts/pages — get_or_create_page must fill both
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            request    = Schema__Action__Request(session_id = session_id                                          ,
                                                  step       = {'action': 'navigate', 'url': 'http://first.test/'})
            service.execute_action(request)

            browser = service.session_manager.get_browser(session_id)
        assert len(browser.contexts)               == 1
        assert len(browser.contexts[0].pages)      == 1
        assert browser.contexts[0].pages[0].goto_calls[0]['url'] == 'http://first.test/'

    def test__reuses_existing_context_and_page_on_second_navigate(self):              # Second call must NOT create a second page
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            request1   = Schema__Action__Request(session_id = session_id                                          ,
                                                  step       = {'action': 'navigate', 'url': 'http://first.test/'})
            request2   = Schema__Action__Request(session_id = session_id                                           ,
                                                  step       = {'action': 'navigate', 'url': 'http://second.test/'})
            service.execute_action(request1)
            service.execute_action(request2)

            browser = service.session_manager.get_browser(session_id)
            page    = browser.contexts[0].pages[0]
        assert len(browser.contexts)          == 1
        assert len(browser.contexts[0].pages) == 1
        assert [c['url'] for c in page.goto_calls] == ['http://first.test/', 'http://second.test/']


class test_execute__click(TestCase):

    def test__click_passes_when_selector_valid(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            service.execute_action(Schema__Action__Request(session_id = session_id                                            ,
                                                            step       = {'action': 'navigate', 'url': 'http://example.com/'}))
            click_req  = Schema__Action__Request(session_id = session_id                                          ,
                                                  step       = {'action': 'click', 'selector': 'button.submit'    })
            response   = service.execute_action(click_req)

            browser = service.session_manager.get_browser(session_id)
            page    = browser.contexts[0].pages[0]
        assert response.step_result.status == Enum__Step__Status.PASSED
        assert len(page.click_calls)       == 1
        assert page.click_calls[0]['selector'] == 'button.submit'


class test_execute__fill(TestCase):

    def test__fill_with_default_clear_first_uses_page_fill(self):                    # clear_first=True (default) routes through page.fill
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            service.execute_action(Schema__Action__Request(session_id = session_id                                            ,
                                                            step       = {'action': 'navigate', 'url': 'http://example.com/'}))
            fill_req   = Schema__Action__Request(session_id = session_id                                                          ,
                                                  step       = {'action': 'fill', 'selector': 'input#q', 'value': 'hello world'}  )
            response   = service.execute_action(fill_req)

            browser = service.session_manager.get_browser(session_id)
            page    = browser.contexts[0].pages[0]
        assert response.step_result.status  == Enum__Step__Status.PASSED
        assert len(page.fill_calls)         == 1
        assert page.fill_calls[0]['selector'] == 'input#q'
        assert page.fill_calls[0]['value']    == 'hello world'

    def test__fill_with_clear_first_false_uses_locator_press_sequentially(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            service.execute_action(Schema__Action__Request(session_id = session_id                                            ,
                                                            step       = {'action': 'navigate', 'url': 'http://example.com/'}))
            fill_req   = Schema__Action__Request(session_id = session_id                                                                                ,
                                                  step       = {'action': 'fill', 'selector': 'input#append', 'value': 'xyz', 'clear_first': False}   )
            response   = service.execute_action(fill_req)

            browser = service.session_manager.get_browser(session_id)
            page    = browser.contexts[0].pages[0]
        assert response.step_result.status == Enum__Step__Status.PASSED
        assert len(page.fill_calls)        == 0                                       # page.fill NOT called
        assert len(page.locators)          == 1
        assert page.locators[0].selector            == 'input#append'
        assert page.locators[0].type_sequences[0]['value'] == 'xyz'


class test_execute__get_content(TestCase):

    def test__get_content_defaults_return_inline_page_content(self):                 # selector=None, content_format=HTML -> page.content()
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            service.execute_action(Schema__Action__Request(session_id = session_id                                            ,
                                                            step       = {'action': 'navigate', 'url': 'http://example.com/'}))
            response   = service.execute_action(Schema__Action__Request(session_id = session_id                        ,
                                                                         step       = {'action': 'get_content'         }))

            browser = service.session_manager.get_browser(session_id)
            page    = browser.contexts[0].pages[0]
        assert response.step_result.status       == Enum__Step__Status.PASSED
        assert response.step_result.content_type == 'text/html'
        assert str(response.step_result.content) == '<html><body>full-page-html</body></html>'
        assert page.content_calls                == 1
        assert response.step_result.artefacts    == []                                # inline_in_response=True (default) -> no sink write

    def test__get_content_with_selector_goes_through_locator_inner_html(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            service.execute_action(Schema__Action__Request(session_id = session_id                                            ,
                                                            step       = {'action': 'navigate', 'url': 'http://example.com/'}))
            response   = service.execute_action(Schema__Action__Request(session_id = session_id                                             ,
                                                                         step       = {'action': 'get_content', 'selector': 'div.main'}    ))

            browser = service.session_manager.get_browser(session_id)
            page    = browser.contexts[0].pages[0]
        assert response.step_result.status == Enum__Step__Status.PASSED
        assert 'html-for:div.main' in str(response.step_result.content)
        assert page.content_calls    == 0                                             # page.content NOT called when selector is set
        assert len(page.locators)    >= 1


class test_execute__get_url(TestCase):

    def test__get_url_returns_current_page_url(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            service.execute_action(Schema__Action__Request(session_id = session_id                                            ,
                                                            step       = {'action': 'navigate', 'url': 'http://after-nav.test/'}))
            response   = service.execute_action(Schema__Action__Request(session_id = session_id                     ,
                                                                         step       = {'action': 'get_url'          }))
        assert response.step_result.status == Enum__Step__Status.PASSED
        assert str(response.step_result.url) == 'http://after-nav.test/'


class test_execute__screenshot(TestCase):

    def test__screenshot_passes_without_sink_when_disabled(self):                    # Default capture_config has screenshot.enabled=False
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            service.execute_action(Schema__Action__Request(session_id = session_id                                            ,
                                                            step       = {'action': 'navigate', 'url': 'http://example.com/'}))
            response   = service.execute_action(Schema__Action__Request(session_id = session_id                          ,
                                                                         step       = {'action': 'screenshot'            }))

            browser = service.session_manager.get_browser(session_id)
            page    = browser.contexts[0].pages[0]
        assert response.step_result.status == Enum__Step__Status.PASSED
        assert len(page.screenshot_calls)  == 1
        assert response.step_result.artefacts == []                                   # Sink disabled -> no ref attached


class test_execute__errors(TestCase):

    def test__404_when_session_unknown(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service = _build_service()
            request = Schema__Action__Request(session_id = 'nope-not-a-real-session'                              ,
                                                step       = {'action': 'navigate', 'url': 'http://x.test/'})
            with pytest.raises(HTTPException) as exc:
                service.execute_action(request)
        assert exc.value.status_code == 404

    def test__422_when_step_action_unknown(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            request    = Schema__Action__Request(session_id = session_id                                    ,
                                                  step       = {'action': 'not_a_real_action'              })
            with pytest.raises(HTTPException) as exc:
                service.execute_action(request)
        assert exc.value.status_code == 422


class test_session_info_updates(TestCase):

    def test__total_actions_bumps_per_action(self):                                   # session_info is returned by reference; assert on the live session after all actions
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'lambda'}):
            service    = _build_service()
            session_id = _open_session(service)
            service.execute_action(Schema__Action__Request(session_id = session_id                                            ,
                                                            step       = {'action': 'navigate', 'url': 'http://example.com/'}))
            service.execute_action(Schema__Action__Request(session_id = session_id                                  ,
                                                            step       = {'action': 'click', 'selector': '#go'     }))
            session = service.session_manager.get(session_id)
        assert session.total_actions == 2

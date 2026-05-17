# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Bedrock__Tool__AWS__Client
#
# Uses a real subclass that injects an in-memory stub agentcore client.
# No mocks, no patches.
#
# Regression coverage for 2026-05-17 user-reported bugs:
#   sg aws bedrock tool browser session start
#     → ParamValidationError: Missing required parameter "browserIdentifier"
#   sg aws bedrock tool code-interpreter session start
#     → ParamValidationError: Missing required parameter "codeInterpreterIdentifier"
#       Unknown parameter "language"
#
# The fakes here STRICTLY enforce the AWS-side parameter contract so the same
# class of bug — calling the API with wrong kwargs — surfaces as a test
# failure, not a runtime traceback.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Tool__AWS__Client import (
    Bedrock__Tool__AWS__Client                                                   ,
    DEFAULT_BROWSER_ID                                                           ,
    DEFAULT_CODE_INTERPRETER_ID                                                  ,
)


# ── In-memory stub agentcore client ───────────────────────────────────────────

_VALID_START_BROWSER_KWARGS          = {'browserIdentifier', 'name', 'sessionTimeoutSeconds', 'clientToken'}
_VALID_START_CODE_INTERPRETER_KWARGS = {'codeInterpreterIdentifier', 'name', 'sessionTimeoutSeconds', 'clientToken', 'traceId', 'traceParent', 'certificates'}
_VALID_INVOKE_BROWSER_KWARGS         = {'browserIdentifier', 'sessionId', 'action'}
_VALID_BROWSER_ACTION_KEYS           = {'mouseClick', 'mouseMove', 'mouseDrag', 'mouseScroll', 'keyType', 'keyPress', 'keyShortcut', 'screenshot'}


class _FakeAgentCoreClient:
    """In-memory AgentCore client that mirrors the boto3 parameter contract."""

    def __init__(self):
        self.calls = []                                                          # record of (api_name, kwargs)

    def start_browser_session(self, **kwargs):
        self.calls.append(('start_browser_session', kwargs))
        # Mirror the AWS-side parameter validation that bit us in prod.
        if 'browserIdentifier' not in kwargs:
            raise TypeError("Missing required parameter: 'browserIdentifier'")
        unknown = set(kwargs) - _VALID_START_BROWSER_KWARGS
        if unknown:
            raise TypeError(f"Unknown parameter(s): {sorted(unknown)}")
        return {'sessionId': 'fake-browser-session-id'}

    def invoke_browser(self, **kwargs):
        self.calls.append(('invoke_browser', kwargs))
        if 'browserIdentifier' not in kwargs:
            raise TypeError("Missing required parameter: 'browserIdentifier'")
        if 'sessionId' not in kwargs:
            raise TypeError("Missing required parameter: 'sessionId'")
        if 'action' not in kwargs:
            raise TypeError("Missing required parameter: 'action'")
        unknown = set(kwargs) - _VALID_INVOKE_BROWSER_KWARGS
        if unknown:
            raise TypeError(f"Unknown parameter(s): {sorted(unknown)}")
        action_keys = set(kwargs['action'])
        invalid_actions = action_keys - _VALID_BROWSER_ACTION_KEYS
        if invalid_actions:
            raise TypeError(f"Invalid action key(s): {sorted(invalid_actions)}")
        if 'screenshot' in kwargs['action']:
            return {'result': {'screenshot': {'bytes': b'\x89PNG-fake-bytes'}}}
        return {'result': {}}

    def start_code_interpreter_session(self, **kwargs):
        self.calls.append(('start_code_interpreter_session', kwargs))
        if 'codeInterpreterIdentifier' not in kwargs:
            raise TypeError("Missing required parameter: 'codeInterpreterIdentifier'")
        unknown = set(kwargs) - _VALID_START_CODE_INTERPRETER_KWARGS
        if unknown:
            raise TypeError(f"Unknown parameter(s): {sorted(unknown)}")
        return {'sessionId': 'fake-code-interpreter-session-id'}


class _Fake_Bedrock__Tool__AWS__Client(Bedrock__Tool__AWS__Client):
    """Subclass overriding the boto3 seam — no mocks, no patches."""

    def __init__(self):
        super().__init__()
        self._fake_agentcore = _FakeAgentCoreClient()

    def agentcore_client(self, region: str = None):
        return self._fake_agentcore

    def current_region(self) -> str:
        return 'us-east-1'


# ── Tests — browser_start ────────────────────────────────────────────────────

class test_browser_start(TestCase):

    def setUp(self):
        self.client = _Fake_Bedrock__Tool__AWS__Client()

    def test__sends_browser_identifier__defaults_to_aws_browser_v1(self):
        # The original bug: no browserIdentifier was sent → AWS ParamValidationError.
        session = self.client.browser_start()
        assert session.session_id == 'fake-browser-session-id'
        api, kwargs = self.client._fake_agentcore.calls[-1]
        assert api                           == 'start_browser_session'
        assert kwargs['browserIdentifier']   == DEFAULT_BROWSER_ID
        assert DEFAULT_BROWSER_ID            == 'aws.browser.v1'                  # documents the AWS-managed sandbox default

    def test__sends_custom_browser_identifier_when_provided(self):
        self.client.browser_start(browser_identifier='custom.browser.v1')
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert kwargs['browserIdentifier']   == 'custom.browser.v1'

    def test__no_unknown_kwargs_are_sent(self):                                  # AWS rejects anything not in its allowed set
        self.client.browser_start()
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert set(kwargs) <= _VALID_START_BROWSER_KWARGS

    def test__region_does_not_leak_into_aws_kwargs(self):                        # `region` is a client-side dispatch concern, not an API param
        self.client.browser_start(region='eu-west-1')
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert 'region' not in kwargs


# ── Tests — browser_screenshot ───────────────────────────────────────────────
# Regression for 2026-05-17: `browser_tool` was the wrong boto3 method name
# (`AttributeError: 'BedrockAgentCore' object has no attribute 'browser_tool'`).
# Correct method is `invoke_browser`, with `screenshot` as an action key.

class test_browser_screenshot(TestCase):

    def setUp(self):
        self.client = _Fake_Bedrock__Tool__AWS__Client()

    def test__calls_invoke_browser_with_screenshot_action(self):
        data = self.client.browser_screenshot('sid-123')
        assert data == b'\x89PNG-fake-bytes'
        api, kwargs = self.client._fake_agentcore.calls[-1]
        assert api                            == 'invoke_browser'                 # NOT 'browser_tool' (the original bug)
        assert kwargs['sessionId']            == 'sid-123'
        assert kwargs['browserIdentifier']    == DEFAULT_BROWSER_ID
        assert 'screenshot' in kwargs['action']
        assert kwargs['action']['screenshot']['format'] == 'PNG'

    def test__honours_custom_browser_identifier(self):
        self.client.browser_screenshot('sid-123', browser_identifier='custom.browser.v1')
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert kwargs['browserIdentifier']    == 'custom.browser.v1'

    def test__extracts_image_bytes_from_nested_result(self):                     # `resp['result']['screenshot']['bytes']`
        data = self.client.browser_screenshot('sid-123')
        assert isinstance(data, bytes)
        assert data == b'\x89PNG-fake-bytes'


# ── Tests — browser_navigate ─────────────────────────────────────────────────
# Regression for 2026-05-17: navigate was calling `browser_tool` (wrong method)
# AND `invoke_browser` has no `navigate` action — only OS-level actions
# (mouse/keyboard/screenshot). Honest behaviour: raise NotImplementedError
# with a message pointing at the right path (Playwright over CDP stream).

class test_browser_navigate(TestCase):

    def setUp(self):
        self.client = _Fake_Bedrock__Tool__AWS__Client()

    def test__raises_not_implemented_with_explanation(self):
        try:
            self.client.browser_navigate('sid-123', 'https://example.com')
        except NotImplementedError as exc:
            msg = str(exc)
            assert 'invoke_browser' in msg
            assert 'CDP' in msg or 'Chrome DevTools Protocol' in msg              # message points the reader at the right next step
            return
        raise AssertionError('Expected NotImplementedError')

    def test__does_not_call_aws_when_unimplemented(self):                        # belt-and-braces: no API call attempt
        try:
            self.client.browser_navigate('sid-123', 'https://example.com')
        except NotImplementedError:
            pass
        assert self.client._fake_agentcore.calls == []                            # nothing was attempted


# ── Tests — code_interpreter_start ───────────────────────────────────────────

class test_code_interpreter_start(TestCase):

    def setUp(self):
        self.client = _Fake_Bedrock__Tool__AWS__Client()

    def test__sends_code_interpreter_identifier__defaults_to_aws_codeinterpreter_v1(self):
        # The original bug: codeInterpreterIdentifier was missing → AWS error.
        session = self.client.code_interpreter_start()
        assert session.session_id == 'fake-code-interpreter-session-id'
        api, kwargs = self.client._fake_agentcore.calls[-1]
        assert api                                  == 'start_code_interpreter_session'
        assert kwargs['codeInterpreterIdentifier']  == DEFAULT_CODE_INTERPRETER_ID
        assert DEFAULT_CODE_INTERPRETER_ID          == 'aws.codeinterpreter.v1'

    def test__sends_custom_code_interpreter_identifier_when_provided(self):
        self.client.code_interpreter_start(code_interpreter_id='custom.codeinterpreter.v1')
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert kwargs['codeInterpreterIdentifier']  == 'custom.codeinterpreter.v1'

    def test__language_is_NOT_sent_to_aws(self):
        # The second half of the original bug: `language` was being sent to
        # `start_code_interpreter_session` but AWS doesn't accept that kwarg.
        # `language` lives ONLY on the local schema for capture metadata.
        self.client.code_interpreter_start(language='javascript')
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert 'language' not in kwargs

    def test__language_is_preserved_on_local_schema(self):                       # capture metadata only
        session = self.client.code_interpreter_start(language='typescript')
        assert session.language == 'typescript'

    def test__default_language_is_python(self):
        session = self.client.code_interpreter_start()
        assert session.language == 'python'

    def test__no_unknown_kwargs_are_sent(self):
        self.client.code_interpreter_start(language='python', region='eu-west-1', code_interpreter_id='custom.ci.v1')
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert set(kwargs) <= _VALID_START_CODE_INTERPRETER_KWARGS

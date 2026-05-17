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
_VALID_STOP_BROWSER_KWARGS           = {'browserIdentifier', 'sessionId', 'clientToken', 'traceId', 'traceParent'}
_VALID_LIST_BROWSER_KWARGS           = {'browserIdentifier', 'maxResults', 'nextToken', 'status'}
_VALID_GET_BROWSER_KWARGS            = {'browserIdentifier', 'sessionId'}
_VALID_STOP_CODE_INTERPRETER_KWARGS  = {'codeInterpreterIdentifier', 'sessionId', 'clientToken', 'traceId', 'traceParent'}
_VALID_LIST_CODE_INTERPRETER_KWARGS  = {'codeInterpreterIdentifier', 'maxResults', 'nextToken', 'status'}
_VALID_INVOKE_CODE_INTERPRETER_KWARGS= {'codeInterpreterIdentifier', 'sessionId', 'name', 'arguments', 'traceId', 'traceParent'}
_VALID_INVOKE_CODE_INTERPRETER_NAMES = {'executeCode', 'executeCommand', 'readFiles', 'listFiles', 'removeFiles', 'writeFiles', 'startCommandExecution', 'getTask', 'stopTask'}


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

    def stop_browser_session(self, **kwargs):
        self.calls.append(('stop_browser_session', kwargs))
        if 'browserIdentifier' not in kwargs:
            raise TypeError("Missing required parameter: 'browserIdentifier'")
        if 'sessionId' not in kwargs:
            raise TypeError("Missing required parameter: 'sessionId'")
        unknown = set(kwargs) - _VALID_STOP_BROWSER_KWARGS
        if unknown:
            raise TypeError(f"Unknown parameter(s): {sorted(unknown)}")
        return {}

    def list_browser_sessions(self, **kwargs):
        self.calls.append(('list_browser_sessions', kwargs))
        if 'browserIdentifier' not in kwargs:
            raise TypeError("Missing required parameter: 'browserIdentifier'")
        unknown = set(kwargs) - _VALID_LIST_BROWSER_KWARGS
        if unknown:
            raise TypeError(f"Unknown parameter(s): {sorted(unknown)}")
        return {'items': [
            {'sessionId': 'sid-1', 'browserIdentifier': kwargs['browserIdentifier'], 'status': 'READY'},
            {'sessionId': 'sid-2', 'browserIdentifier': kwargs['browserIdentifier'], 'status': 'TERMINATED'},
        ]}

    def get_browser_session(self, **kwargs):
        self.calls.append(('get_browser_session', kwargs))
        if 'browserIdentifier' not in kwargs:
            raise TypeError("Missing required parameter: 'browserIdentifier'")
        if 'sessionId' not in kwargs:
            raise TypeError("Missing required parameter: 'sessionId'")
        unknown = set(kwargs) - _VALID_GET_BROWSER_KWARGS
        if unknown:
            raise TypeError(f"Unknown parameter(s): {sorted(unknown)}")
        return {
            'sessionId': kwargs['sessionId'],
            'browserIdentifier': kwargs['browserIdentifier'],
            'status': 'READY',
            'streams': {
                'automationStream': {'streamEndpoint': 'wss://fake.example/automation/' + kwargs['sessionId']},
                'liveViewStream':   {'streamEndpoint': 'wss://fake.example/live/'       + kwargs['sessionId']},
            },
        }

    def stop_code_interpreter_session(self, **kwargs):
        self.calls.append(('stop_code_interpreter_session', kwargs))
        if 'codeInterpreterIdentifier' not in kwargs:
            raise TypeError("Missing required parameter: 'codeInterpreterIdentifier'")
        if 'sessionId' not in kwargs:
            raise TypeError("Missing required parameter: 'sessionId'")
        unknown = set(kwargs) - _VALID_STOP_CODE_INTERPRETER_KWARGS
        if unknown:
            raise TypeError(f"Unknown parameter(s): {sorted(unknown)}")
        return {}

    def list_code_interpreter_sessions(self, **kwargs):
        self.calls.append(('list_code_interpreter_sessions', kwargs))
        if 'codeInterpreterIdentifier' not in kwargs:
            raise TypeError("Missing required parameter: 'codeInterpreterIdentifier'")
        unknown = set(kwargs) - _VALID_LIST_CODE_INTERPRETER_KWARGS
        if unknown:
            raise TypeError(f"Unknown parameter(s): {sorted(unknown)}")
        return {'items': [
            {'sessionId': 'sid-1', 'codeInterpreterIdentifier': kwargs['codeInterpreterIdentifier'], 'status': 'READY'},
        ]}

    def invoke_code_interpreter(self, **kwargs):
        self.calls.append(('invoke_code_interpreter', kwargs))
        if 'codeInterpreterIdentifier' not in kwargs:
            raise TypeError("Missing required parameter: 'codeInterpreterIdentifier'")
        if 'name' not in kwargs:
            raise TypeError("Missing required parameter: 'name'")
        unknown = set(kwargs) - _VALID_INVOKE_CODE_INTERPRETER_KWARGS
        if unknown:
            raise TypeError(f"Unknown parameter(s): {sorted(unknown)}")
        if kwargs['name'] not in _VALID_INVOKE_CODE_INTERPRETER_NAMES:
            raise TypeError(f"Invalid name: {kwargs['name']!r}")
        return {'output': 'fake-result'}


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


# ── Tests — browser_navigate (returns CDP stream endpoints) ──────────────────
# Now returns the streamEndpoint dict from get_browser_session so the caller
# can hand it to an external Playwright/CDP client. (Full in-process navigate
# is a follow-up — needs Playwright connected over CDP to the SigV4-signed
# stream URL.)

class test_browser_navigate(TestCase):

    def setUp(self):
        self.client = _Fake_Bedrock__Tool__AWS__Client()

    def test__returns_stream_endpoints_for_external_playwright(self):
        resp = self.client.browser_navigate('sid-abc', 'https://example.com')
        assert resp['status']                              == 'STREAM_ENDPOINT_RETURNED'
        assert resp['requested_url']                       == 'https://example.com'
        assert resp['stream_endpoints']['automation']      == 'wss://fake.example/automation/sid-abc'
        assert resp['stream_endpoints']['live_view']       == 'wss://fake.example/live/sid-abc'

    def test__calls_get_browser_session_with_correct_kwargs(self):
        self.client.browser_navigate('sid-abc', 'https://example.com')
        api, kwargs = self.client._fake_agentcore.calls[-1]
        assert api                          == 'get_browser_session'
        assert kwargs['sessionId']          == 'sid-abc'
        assert kwargs['browserIdentifier']  == DEFAULT_BROWSER_ID

    def test__honours_custom_browser_identifier(self):
        self.client.browser_navigate('sid-abc', 'https://example.com', browser_identifier='custom.browser.v1')
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert kwargs['browserIdentifier']  == 'custom.browser.v1'

    def test__no_unknown_kwargs_are_sent(self):
        self.client.browser_navigate('sid-abc', 'https://example.com')
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert set(kwargs) <= _VALID_GET_BROWSER_KWARGS


# ── Tests — browser_list / browser_stop (regression: also need identifier) ───

class test_browser_list_and_stop(TestCase):

    def setUp(self):
        self.client = _Fake_Bedrock__Tool__AWS__Client()

    def test__list_sends_browser_identifier(self):                               # regression: was failing with ParamValidationError
        sessions = self.client.browser_list()
        assert len(sessions) == 2
        assert str(sessions[0].session_id) == 'sid-1'
        api, kwargs = self.client._fake_agentcore.calls[-1]
        assert api                          == 'list_browser_sessions'
        assert kwargs['browserIdentifier']  == DEFAULT_BROWSER_ID

    def test__list_reads_items_key_not_sessions(self):                           # AWS field is `items`, not `sessions`
        sessions = self.client.browser_list()
        assert len(sessions) == 2                                                # both items returned

    def test__list_honours_custom_browser_identifier(self):
        self.client.browser_list(browser_identifier='custom.browser.v1')
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert kwargs['browserIdentifier']  == 'custom.browser.v1'

    def test__stop_sends_browser_identifier_and_session_id(self):
        self.client.browser_stop('sid-xyz')
        api, kwargs = self.client._fake_agentcore.calls[-1]
        assert api                          == 'stop_browser_session'
        assert kwargs['browserIdentifier']  == DEFAULT_BROWSER_ID
        assert kwargs['sessionId']          == 'sid-xyz'

    def test__stop_honours_custom_browser_identifier(self):
        self.client.browser_stop('sid-xyz', browser_identifier='custom.browser.v1')
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert kwargs['browserIdentifier']  == 'custom.browser.v1'


# ── Tests — browser_get / browser_stream_endpoints ───────────────────────────

class test_browser_get_and_stream_endpoints(TestCase):

    def setUp(self):
        self.client = _Fake_Bedrock__Tool__AWS__Client()

    def test__browser_get_returns_full_session_details(self):
        resp = self.client.browser_get('sid-abc')
        assert resp['sessionId']                                     == 'sid-abc'
        assert resp['streams']['automationStream']['streamEndpoint'] == 'wss://fake.example/automation/sid-abc'

    def test__browser_stream_endpoints_extracts_both_streams(self):
        endpoints = self.client.browser_stream_endpoints('sid-abc')
        assert endpoints['automation'] == 'wss://fake.example/automation/sid-abc'
        assert endpoints['live_view']  == 'wss://fake.example/live/sid-abc'


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


# ── Tests — code_interpreter_run / stop / list (identifier-fix regressions) ─

class test_code_interpreter_run_stop_list(TestCase):

    def setUp(self):
        self.client = _Fake_Bedrock__Tool__AWS__Client()

    def test__run_sends_correct_invoke_shape(self):                              # name='executeCode' + arguments={code, language}
        self.client.code_interpreter_run('sid-1', 'print("hi")')
        api, kwargs = self.client._fake_agentcore.calls[-1]
        assert api                                  == 'invoke_code_interpreter'
        assert kwargs['codeInterpreterIdentifier']  == DEFAULT_CODE_INTERPRETER_ID
        assert kwargs['sessionId']                  == 'sid-1'
        assert kwargs['name']                       == 'executeCode'
        assert kwargs['arguments']                  == {'code': 'print("hi")', 'language': 'python'}

    def test__run_honours_language_and_custom_identifier(self):
        self.client.code_interpreter_run('sid-1', 'console.log("hi")', language='javascript', code_interpreter_id='custom.ci.v1')
        _api, kwargs = self.client._fake_agentcore.calls[-1]
        assert kwargs['codeInterpreterIdentifier']  == 'custom.ci.v1'
        assert kwargs['arguments']['language']      == 'javascript'

    def test__stop_sends_identifier_and_session_id(self):                        # regression: identifier was missing
        self.client.code_interpreter_stop('sid-1')
        api, kwargs = self.client._fake_agentcore.calls[-1]
        assert api                                  == 'stop_code_interpreter_session'
        assert kwargs['codeInterpreterIdentifier']  == DEFAULT_CODE_INTERPRETER_ID
        assert kwargs['sessionId']                  == 'sid-1'

    def test__list_sends_identifier_and_reads_items(self):                       # regression: identifier missing AND wrong response key
        sessions = self.client.code_interpreter_list()
        assert len(sessions) == 1
        api, kwargs = self.client._fake_agentcore.calls[-1]
        assert api                                  == 'list_code_interpreter_sessions'
        assert kwargs['codeInterpreterIdentifier']  == DEFAULT_CODE_INTERPRETER_ID

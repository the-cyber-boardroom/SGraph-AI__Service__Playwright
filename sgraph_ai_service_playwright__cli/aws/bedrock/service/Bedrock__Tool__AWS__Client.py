# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Tool__AWS__Client
# AgentCore SDK boundary for Bedrock inline tools: browser and code-interpreter.
#
# EXPERIMENTAL: uses boto3 'bedrock-agentcore-control' and
# 'bedrock-agentcore' namespaces. When the AgentCore Python SDK stabilises,
# replace the boto3 surface here — CLI signatures stay unchanged.
#
# ═══════════════════════════════════════════════════════════════════════════════

from botocore.exceptions                                                         import ClientError
from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver                              import Aws__Region__Resolver
from sgraph_ai_service_playwright__cli.aws.bedrock.collections.List__Schema__Bedrock__Tool__Session import List__Schema__Bedrock__Tool__Session
from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Tool__Type                  import Enum__Bedrock__Tool__Type
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Session_Id         import Safe_Str__Bedrock__Session_Id
from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Tool__Session           import Schema__Bedrock__Tool__Session
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session                         import Sg__Aws__Session

# AWS-managed default AgentCore tool identifiers. AgentCore start-session APIs
# require an identifier of a previously-created (or built-in) tool resource.
# `aws.browser.v1` and `aws.codeinterpreter.v1` are the always-available
# system sandboxes — using them avoids the control-plane round-trip to
# create-then-start a custom tool resource.
DEFAULT_BROWSER_ID          = 'aws.browser.v1'
DEFAULT_CODE_INTERPRETER_ID = 'aws.codeinterpreter.v1'


class Bedrock__Tool__AWS__Client(Type_Safe):
    session : Sg__Aws__Session = None                                            # cached session — injected or lazy-init via setup()

    def setup(self):                                                              # idempotent — noop if session already set
        if self.session is None:
            self.session = Sg__Aws__Session.from_context()
        return self

    def current_region(self) -> str:
        return str(Aws__Region__Resolver().resolve())

    def agentcore_client(self, region: str = None):                              # AgentCore runtime client (browser + code-interpreter)
        self.setup()
        return self.session.boto3_client_from_context('bedrock-agentcore', region=region or self.current_region())

    def agentcore_control_client(self, region: str = None):                      # AgentCore control-plane client
        self.setup()
        return self.session.boto3_client_from_context('bedrock-agentcore-control', region=region or self.current_region())

    # ── Browser sessions ──────────────────────────────────────────────────────

    def browser_start(self, region: str = None, browser_identifier: str = None,
                      viewport: dict = None, session_timeout_seconds: int = None,
                      ) -> Schema__Bedrock__Tool__Session:
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        # Only include optional kwargs when set — AWS rejects `viewPort=None`.
        kwargs = dict(browserIdentifier=browser_identifier or DEFAULT_BROWSER_ID)
        if viewport:
            kwargs['viewPort']              = viewport
        if session_timeout_seconds:
            kwargs['sessionTimeoutSeconds'] = session_timeout_seconds
        resp   = client.start_browser_session(**kwargs)
        sid    = resp.get('sessionId', '')
        try:
            safe_sid = Safe_Str__Bedrock__Session_Id(sid)
        except ValueError:
            safe_sid = Safe_Str__Bedrock__Session_Id('')
        return Schema__Bedrock__Tool__Session(session_id   = safe_sid                   ,
                                              tool_type    = Enum__Bedrock__Tool__Type.BROWSER,
                                              status       = 'STARTING'                 ,
                                              language     = ''                          ,
                                              region       = effective_region            ,
                                              capture_path = ''                          )

    def browser_get(self, session_id: str, region: str = None, browser_identifier: str = None) -> dict:
        """Fetch full session details, including the CDP streamEndpoint."""
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        return client.get_browser_session(browserIdentifier=browser_identifier or DEFAULT_BROWSER_ID,
                                          sessionId        =session_id                              )

    def browser_stream_endpoints(self, session_id: str, region: str = None, browser_identifier: str = None) -> dict:
        """Return {'automation': <url>, 'live_view': <url>} for the session.
        URLs are CDP WebSocket endpoints — connect with Playwright via
        `chromium.connect_over_cdp(url)` (auth: SigV4-signed; see docstring
        on browser_navigate for details)."""
        resp    = self.browser_get(session_id, region=region, browser_identifier=browser_identifier)
        streams = resp.get('streams', {}) or {}
        return dict(automation = (streams.get('automationStream', {}) or {}).get('streamEndpoint', ''),
                    live_view  = (streams.get('liveViewStream',  {}) or {}).get('streamEndpoint', ''))

    def browser_navigate(self, session_id: str, url: str, region: str = None, browser_identifier: str = None) -> dict:
        # AWS `invoke_browser` only exposes OS-level actions (mouseClick,
        # keyType, screenshot, etc.) — there is NO `navigate` action in the
        # BrowserAction union. URL navigation requires connecting to the
        # session's CDP/WebSocket stream endpoint with Playwright (over CDP).
        #
        # Auth: the streamEndpoint URL is a wss:// link that must be SigV4-
        # signed with the same AWS credentials used to start the session.
        # boto3 doesn't sign WebSockets natively — use botocore's
        # `SigV4QueryAuth` to pre-sign the URL, or wrap the connect call
        # in a request signer.
        #
        # For now we return the streamEndpoint dict so the caller can hand
        # it to an external Playwright/CDP client; the actual navigate
        # round-trip lives in a follow-up slice.
        endpoints = self.browser_stream_endpoints(session_id, region=region, browser_identifier=browser_identifier)
        return dict(status            = 'STREAM_ENDPOINT_RETURNED'                                    ,
                    requested_url     = url                                                            ,
                    note              = 'Connect Playwright via chromium.connect_over_cdp(automation).',
                    auth_hint         = 'streamEndpoint requires SigV4 signing with AWS credentials.'  ,
                    stream_endpoints  = endpoints                                                      )

    def browser_screenshot(self, session_id: str, region: str = None, browser_identifier: str = None) -> bytes:
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        resp   = client.invoke_browser(browserIdentifier=browser_identifier or DEFAULT_BROWSER_ID,
                                       sessionId        =session_id                              ,
                                       action           =dict(screenshot=dict(format='PNG'))     )
        # AWS shape (verified against boto3 InvokeBrowser output_shape):
        #   {'result': {'screenshot': {'status': 'SUCCESS', 'data': b'...', 'error': '...'}}, 'sessionId': '...'}
        # Field is `data` (blob), NOT `bytes`. Also surface AWS-side errors
        # instead of silently returning empty bytes (caller used to print
        # "Screenshot saved" even when nothing was captured).
        result             = resp.get('result',     {}) or {}
        screenshot_payload = result.get('screenshot', {}) or {}
        status             = screenshot_payload.get('status', '')
        error              = screenshot_payload.get('error',  '')
        data               = screenshot_payload.get('data',   b'')
        if not data:
            raise RuntimeError(f'Screenshot returned no data (status={status!r}, error={error!r}).')
        return data

    def browser_stop(self, session_id: str, region: str = None, browser_identifier: str = None) -> None:
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        client.stop_browser_session(browserIdentifier=browser_identifier or DEFAULT_BROWSER_ID,
                                    sessionId        =session_id                              )

    def browser_list(self, region: str = None, browser_identifier: str = None) -> List__Schema__Bedrock__Tool__Session:
        effective_region = region or self.current_region()
        result           = List__Schema__Bedrock__Tool__Session()
        client           = self.agentcore_client(effective_region)
        resp             = client.list_browser_sessions(browserIdentifier=browser_identifier or DEFAULT_BROWSER_ID)
        for item in resp.get('items', []):                                       # AWS returns `items`, not `sessions`
            sid = item.get('sessionId', '')
            try:
                safe_sid = Safe_Str__Bedrock__Session_Id(sid)
            except ValueError:
                safe_sid = Safe_Str__Bedrock__Session_Id('')
            result.append(Schema__Bedrock__Tool__Session(
                session_id   = safe_sid                         ,
                tool_type    = Enum__Bedrock__Tool__Type.BROWSER,
                status       = item.get('status', 'UNKNOWN')    ,
                language     = ''                                ,
                region       = effective_region                  ,
                capture_path = ''                                ))
        return result

    # ── Code-interpreter sessions ─────────────────────────────────────────────

    def code_interpreter_start(self,
                               language              : str = 'python',
                               region                : str = None    ,
                               code_interpreter_id   : str = None    ,
                               ) -> Schema__Bedrock__Tool__Session:
        # `language` is tracked locally for capture metadata; it is NOT a
        # valid parameter on the AWS `start_code_interpreter_session` API
        # (which accepts: codeInterpreterIdentifier, name, sessionTimeoutSeconds,
        # certificates, clientToken, traceId, traceParent).
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        resp   = client.start_code_interpreter_session(codeInterpreterIdentifier=code_interpreter_id or DEFAULT_CODE_INTERPRETER_ID)
        sid    = resp.get('sessionId', '')
        try:
            safe_sid = Safe_Str__Bedrock__Session_Id(sid)
        except ValueError:
            safe_sid = Safe_Str__Bedrock__Session_Id('')
        return Schema__Bedrock__Tool__Session(session_id   = safe_sid                                  ,
                                              tool_type    = Enum__Bedrock__Tool__Type.CODE_INTERPRETER,
                                              status       = 'STARTING'                                ,
                                              language     = language                                  ,
                                              region       = effective_region                          ,
                                              capture_path = ''                                        )

    def code_interpreter_run(self, session_id: str, code: str, language: str = 'python', region: str = None, code_interpreter_id: str = None) -> dict:
        # AWS `invoke_code_interpreter` takes a tool `name` + `arguments`
        # structure. For raw code execution use name='executeCode'.
        # Valid names: executeCode, executeCommand, readFiles, listFiles,
        # removeFiles, writeFiles, startCommandExecution, getTask, stopTask.
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        return client.invoke_code_interpreter(codeInterpreterIdentifier=code_interpreter_id or DEFAULT_CODE_INTERPRETER_ID,
                                              sessionId                =session_id                                        ,
                                              name                     ='executeCode'                                     ,
                                              arguments                =dict(code=code, language=language)                )

    def code_interpreter_stop(self, session_id: str, region: str = None, code_interpreter_id: str = None) -> None:
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        client.stop_code_interpreter_session(codeInterpreterIdentifier=code_interpreter_id or DEFAULT_CODE_INTERPRETER_ID,
                                             sessionId                =session_id                                        )

    def code_interpreter_list(self, region: str = None, code_interpreter_id: str = None) -> List__Schema__Bedrock__Tool__Session:
        effective_region = region or self.current_region()
        result           = List__Schema__Bedrock__Tool__Session()
        client           = self.agentcore_client(effective_region)
        resp             = client.list_code_interpreter_sessions(codeInterpreterIdentifier=code_interpreter_id or DEFAULT_CODE_INTERPRETER_ID)
        for item in resp.get('items', []):                                       # AWS returns `items`, not `sessions`
            sid = item.get('sessionId', '')
            try:
                safe_sid = Safe_Str__Bedrock__Session_Id(sid)
            except ValueError:
                safe_sid = Safe_Str__Bedrock__Session_Id('')
            result.append(Schema__Bedrock__Tool__Session(
                session_id   = safe_sid                                           ,
                tool_type    = Enum__Bedrock__Tool__Type.CODE_INTERPRETER         ,
                status       = item.get('status', 'UNKNOWN')                      ,
                language     = item.get('language', '')                            ,
                region       = effective_region                                    ,
                capture_path = ''                                                  ))
        return result

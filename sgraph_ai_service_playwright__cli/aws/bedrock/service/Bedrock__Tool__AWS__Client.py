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

    def browser_start(self, region: str = None, browser_identifier: str = None) -> Schema__Bedrock__Tool__Session:
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        resp   = client.start_browser_session(browserIdentifier=browser_identifier or DEFAULT_BROWSER_ID)
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

    def browser_navigate(self, session_id: str, url: str, region: str = None) -> dict:
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        return client.browser_tool(sessionId=session_id,
                                   action   =dict(type='navigate', url=url))

    def browser_screenshot(self, session_id: str, region: str = None) -> bytes:
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        resp   = client.browser_tool(sessionId=session_id,
                                     action   =dict(type='screenshot'))
        return resp.get('imageData', b'')

    def browser_stop(self, session_id: str, region: str = None) -> None:
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        client.stop_browser_session(sessionId=session_id)

    def browser_list(self, region: str = None) -> List__Schema__Bedrock__Tool__Session:
        effective_region = region or self.current_region()
        result           = List__Schema__Bedrock__Tool__Session()
        client           = self.agentcore_client(effective_region)
        resp             = client.list_browser_sessions()
        for item in resp.get('sessions', []):
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

    def code_interpreter_run(self, session_id: str, code: str, region: str = None) -> dict:
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        return client.invoke_code_interpreter(sessionId=session_id, code=code)

    def code_interpreter_stop(self, session_id: str, region: str = None) -> None:
        effective_region = region or self.current_region()
        client = self.agentcore_client(effective_region)
        client.stop_code_interpreter_session(sessionId=session_id)

    def code_interpreter_list(self, region: str = None) -> List__Schema__Bedrock__Tool__Session:
        effective_region = region or self.current_region()
        result           = List__Schema__Bedrock__Tool__Session()
        client           = self.agentcore_client(effective_region)
        resp             = client.list_code_interpreter_sessions()
        for item in resp.get('sessions', []):
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

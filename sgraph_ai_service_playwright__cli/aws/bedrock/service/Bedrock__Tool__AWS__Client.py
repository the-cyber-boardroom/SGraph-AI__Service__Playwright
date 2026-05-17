# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Tool__AWS__Client
# AgentCore SDK boundary for Bedrock inline tools: browser and code-interpreter.
#
# EXPERIMENTAL: uses boto3 'bedrock-agentcore-control' and
# 'bedrock-agentcore' namespaces. When the AgentCore Python SDK stabilises,
# replace the boto3 surface here — CLI signatures stay unchanged.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                     # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.collections.List__Schema__Bedrock__Tool__Session import List__Schema__Bedrock__Tool__Session
from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Tool__Type                  import Enum__Bedrock__Tool__Type
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Session_Id         import Safe_Str__Bedrock__Session_Id
from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Tool__Session           import Schema__Bedrock__Tool__Session

FALLBACK_REGION = 'us-east-1'


class Bedrock__Tool__AWS__Client(Type_Safe):

    def current_region(self) -> str:
        region = boto3.session.Session().region_name
        return region if region else FALLBACK_REGION

    def agentcore_client(self, region: str = None):                              # AgentCore runtime client (browser + code-interpreter)
        return boto3.client('bedrock-agentcore',
                            region_name=region or self.current_region())

    def agentcore_control_client(self, region: str = None):                      # AgentCore control-plane client
        return boto3.client('bedrock-agentcore-control',
                            region_name=region or self.current_region())

    # ── Browser sessions ──────────────────────────────────────────────────────

    def browser_start(self, region: str = None) -> Schema__Bedrock__Tool__Session:
        effective_region = region or self.current_region()
        try:
            client = self.agentcore_client(effective_region)
            resp   = client.start_browser_session()
            sid    = resp.get('sessionId', '')
        except Exception as exc:
            raise RuntimeError(f'browser session start failed: {exc}') from exc
        try:
            safe_sid = Safe_Str__Bedrock__Session_Id(sid)
        except Exception:
            safe_sid = Safe_Str__Bedrock__Session_Id('')
        return Schema__Bedrock__Tool__Session(session_id   = safe_sid                   ,
                                              tool_type    = Enum__Bedrock__Tool__Type.BROWSER,
                                              status       = 'STARTING'                 ,
                                              language     = ''                          ,
                                              region       = effective_region            ,
                                              capture_path = ''                          )

    def browser_navigate(self, session_id: str, url: str, region: str = None) -> dict:
        effective_region = region or self.current_region()
        try:
            client = self.agentcore_client(effective_region)
            resp   = client.browser_tool(sessionId=session_id,
                                         action   =dict(type='navigate', url=url))
            return resp
        except Exception as exc:
            raise RuntimeError(f'browser navigate failed: {exc}') from exc

    def browser_screenshot(self, session_id: str, region: str = None) -> bytes:
        effective_region = region or self.current_region()
        try:
            client = self.agentcore_client(effective_region)
            resp   = client.browser_tool(sessionId=session_id,
                                         action   =dict(type='screenshot'))
            return resp.get('imageData', b'')
        except Exception as exc:
            raise RuntimeError(f'browser screenshot failed: {exc}') from exc

    def browser_stop(self, session_id: str, region: str = None) -> bool:
        effective_region = region or self.current_region()
        try:
            client = self.agentcore_client(effective_region)
            client.stop_browser_session(sessionId=session_id)
            return True
        except Exception:
            return False

    def browser_list(self, region: str = None) -> List__Schema__Bedrock__Tool__Session:
        effective_region = region or self.current_region()
        result           = List__Schema__Bedrock__Tool__Session()
        try:
            client = self.agentcore_client(effective_region)
            resp   = client.list_browser_sessions()
            for item in resp.get('sessions', []):
                sid = item.get('sessionId', '')
                try:
                    safe_sid = Safe_Str__Bedrock__Session_Id(sid)
                except Exception:
                    safe_sid = Safe_Str__Bedrock__Session_Id('')
                result.append(Schema__Bedrock__Tool__Session(
                    session_id   = safe_sid                         ,
                    tool_type    = Enum__Bedrock__Tool__Type.BROWSER,
                    status       = item.get('status', 'UNKNOWN')    ,
                    language     = ''                                ,
                    region       = effective_region                  ,
                    capture_path = ''                                ))
        except Exception:
            pass
        return result

    # ── Code-interpreter sessions ─────────────────────────────────────────────

    def code_interpreter_start(self, language: str = 'python', region: str = None) -> Schema__Bedrock__Tool__Session:
        effective_region = region or self.current_region()
        try:
            client = self.agentcore_client(effective_region)
            resp   = client.start_code_interpreter_session(language=language)
            sid    = resp.get('sessionId', '')
        except Exception as exc:
            raise RuntimeError(f'code-interpreter session start failed: {exc}') from exc
        try:
            safe_sid = Safe_Str__Bedrock__Session_Id(sid)
        except Exception:
            safe_sid = Safe_Str__Bedrock__Session_Id('')
        return Schema__Bedrock__Tool__Session(session_id   = safe_sid                                  ,
                                              tool_type    = Enum__Bedrock__Tool__Type.CODE_INTERPRETER,
                                              status       = 'STARTING'                                ,
                                              language     = language                                  ,
                                              region       = effective_region                          ,
                                              capture_path = ''                                        )

    def code_interpreter_run(self, session_id: str, code: str, region: str = None) -> dict:
        effective_region = region or self.current_region()
        try:
            client = self.agentcore_client(effective_region)
            resp   = client.invoke_code_interpreter(sessionId=session_id, code=code)
            return resp
        except Exception as exc:
            raise RuntimeError(f'code-interpreter run failed: {exc}') from exc

    def code_interpreter_stop(self, session_id: str, region: str = None) -> bool:
        effective_region = region or self.current_region()
        try:
            client = self.agentcore_client(effective_region)
            client.stop_code_interpreter_session(sessionId=session_id)
            return True
        except Exception:
            return False

    def code_interpreter_list(self, region: str = None) -> List__Schema__Bedrock__Tool__Session:
        effective_region = region or self.current_region()
        result           = List__Schema__Bedrock__Tool__Session()
        try:
            client = self.agentcore_client(effective_region)
            resp   = client.list_code_interpreter_sessions()
            for item in resp.get('sessions', []):
                sid = item.get('sessionId', '')
                try:
                    safe_sid = Safe_Str__Bedrock__Session_Id(sid)
                except Exception:
                    safe_sid = Safe_Str__Bedrock__Session_Id('')
                result.append(Schema__Bedrock__Tool__Session(
                    session_id   = safe_sid                                           ,
                    tool_type    = Enum__Bedrock__Tool__Type.CODE_INTERPRETER         ,
                    status       = item.get('status', 'UNKNOWN')                      ,
                    language     = item.get('language', '')                            ,
                    region       = effective_region                                    ,
                    capture_path = ''                                                  ))
        except Exception:
            pass
        return result

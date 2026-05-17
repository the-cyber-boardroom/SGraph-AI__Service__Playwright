# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Agent__AWS__Client
# AgentCore SDK boundary for Bedrock Agents (create, invoke, list, get, stop,
# memory list/clear, tools add).
#
# EXPERIMENTAL: the AgentCore Python SDK ('bedrock-agentcore') is not yet
# generally available. This class uses the boto3 'bedrock-agent' and
# 'bedrock-agent-runtime' surfaces as a fallback.
#
# When bedrock_agentcore becomes available, replace the boto3 calls below with
# the SDK calls — the public method signatures stay the same.
#
# ═══════════════════════════════════════════════════════════════════════════════

from botocore.exceptions                                                         import ClientError
from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver               import Aws__Region__Resolver
from sgraph_ai_service_playwright__cli.aws.bedrock.collections.List__Schema__Bedrock__Agent import List__Schema__Bedrock__Agent
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Agent_Arn  import Safe_Str__Bedrock__Agent_Arn
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Model_Id   import Safe_Str__Bedrock__Model_Id
from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Agent           import Schema__Bedrock__Agent
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session                 import Sg__Aws__Session


class Bedrock__Agent__AWS__Client(Type_Safe):
    session : Sg__Aws__Session = None                                            # cached session — injected or lazy-init via setup()

    def setup(self):                                                              # idempotent — noop if session already set
        if self.session is None:
            self.session = Sg__Aws__Session.from_context()
        return self

    def client(self, region: str = None):                                        # boto3 control-plane client for Agents
        self.setup()
        return self.session.boto3_client_from_context('bedrock-agent', region=region or self.current_region())

    def runtime_client(self, region: str = None):                                # boto3 runtime client for invoke
        self.setup()
        return self.session.boto3_client_from_context('bedrock-agent-runtime', region=region or self.current_region())

    def current_region(self) -> str:
        return str(Aws__Region__Resolver().resolve())

    # ── Agent lifecycle ───────────────────────────────────────────────────────

    def create_agent(self, name: str, model_id: str, tools: str = '',
                     memory: str = 'none', region: str = None) -> Schema__Bedrock__Agent:
        effective_region = region or self.current_region()
        agentc           = self.client(effective_region)
        kwargs           = dict(agentName            = name                    ,
                                foundationModel      = model_id                ,
                                agentResourceRoleArn = ''                      )    # Role ARN managed externally
        resp      = agentc.create_agent(**kwargs)
        agent_raw = resp.get('agent', {})
        return self.map_agent(agent_raw, tools=tools, memory=memory, region=effective_region)

    def list_agents(self, region: str = None) -> List__Schema__Bedrock__Agent:
        effective_region = region or self.current_region()
        agentc           = self.client(effective_region)
        result    = List__Schema__Bedrock__Agent()
        paginator = agentc.get_paginator('list_agents')
        for page in paginator.paginate():
            for item in page.get('agentSummaries', []):
                agent = self.map_agent_summary(item, effective_region)
                if agent:
                    result.append(agent)
        return result

    def get_agent(self, agent_id: str, region: str = None) -> Schema__Bedrock__Agent:
        effective_region = region or self.current_region()
        agentc           = self.client(effective_region)
        try:
            resp = agentc.get_agent(agentId=agent_id)
            return self.map_agent(resp.get('agent', {}), region=effective_region)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'ResourceNotFoundException':
                return None
            raise

    def invoke_agent(self, agent_id: str, alias_id: str, session_id: str,
                     prompt: str, region: str = None) -> dict:
        effective_region = region or self.current_region()
        runtime          = self.runtime_client(effective_region)
        resp             = runtime.invoke_agent(agentId        = agent_id  ,
                                                agentAliasId   = alias_id  ,
                                                sessionId      = session_id,
                                                inputText      = prompt    )
        completion       = resp.get('completion', {})
        text_parts       = []
        for event in completion:
            chunk = event.get('chunk', {})
            if 'bytes' in chunk:
                text_parts.append(chunk['bytes'].decode('utf-8', errors='replace'))
        return {'text': ''.join(text_parts), 'session_id': session_id}

    def stop_session(self, session_id: str, agent_id: str,
                     alias_id: str, region: str = None) -> None:
        effective_region = region or self.current_region()
        runtime          = self.runtime_client(effective_region)
        runtime.end_session(agentId      = agent_id  ,
                            agentAliasId = alias_id  ,
                            sessionId    = session_id)

    # ── Mapping helpers ───────────────────────────────────────────────────────

    def map_agent(self, raw: dict, tools: str = '', memory: str = 'none',
                  region: str = '') -> Schema__Bedrock__Agent:
        agent_id   = raw.get('agentId',   '')
        agent_arn  = raw.get('agentArn',  '')
        agent_name = raw.get('agentName', '')
        model_id   = raw.get('foundationModel', '')
        status     = raw.get('agentStatus', 'UNKNOWN')
        try:
            safe_arn = Safe_Str__Bedrock__Agent_Arn(agent_arn)
        except ValueError:
            safe_arn = Safe_Str__Bedrock__Agent_Arn('')
        try:
            safe_mid = Safe_Str__Bedrock__Model_Id(model_id)
        except ValueError:
            safe_mid = Safe_Str__Bedrock__Model_Id('')
        return Schema__Bedrock__Agent(agent_id    = agent_id   ,
                                      agent_arn   = safe_arn   ,
                                      agent_name  = agent_name ,
                                      model_id    = safe_mid   ,
                                      status      = status     ,
                                      tools       = tools      ,
                                      memory      = memory     ,
                                      region      = region     ,
                                      capture_path= ''         )

    def map_agent_summary(self, raw: dict, region: str) -> Schema__Bedrock__Agent:
        return self.map_agent(raw, region=region)

# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Observability__AWS__Client
# Sole AWS boundary for the observability sub-package. Every boto3 import and
# every SigV4 HTTP call lives here so Observability__Service can remain pure
# Python + Type_Safe schemas.
#
# FOLLOW-UP: the rest of the repo forbids direct boto3 use (CLAUDE.md rule 8)
# and routes AWS operations through osbot-aws. AMP / OpenSearch / Grafana do
# not yet have osbot-aws wrappers, so this module is a pragmatic exception
# until one is added. Keep the boundary narrow; never import boto3 outside
# this file.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Dict

import boto3                                                                        # boto3 EXCEPTION — boto3.Session() used for SigV4 credentials only; service clients use Sg__Aws__Session
import requests
from botocore.auth                                                                  import SigV4Auth
from botocore.awsrequest                                                            import AWSRequest

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.observability.enums.Enum__Component__Delete__Outcome      import Enum__Component__Delete__Outcome
from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Kind          import Enum__Stack__Component__Kind
from sgraph_ai_service_playwright__cli.observability.enums.Enum__Stack__Component__Status        import Enum__Stack__Component__Status
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__AMP               import Schema__Stack__Component__AMP
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__Delete__Result    import Schema__Stack__Component__Delete__Result
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__OpenSearch        import Schema__Stack__Component__OpenSearch
from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__Grafana           import Schema__Stack__Component__Grafana


AMP_STATUS_MAP = {'ACTIVE'       : Enum__Stack__Component__Status.ACTIVE  ,        # AWS AMP exposes these status codes on workspace.status.statusCode
                  'CREATING'     : Enum__Stack__Component__Status.CREATING,
                  'UPDATING'     : Enum__Stack__Component__Status.UPDATING,
                  'DELETING'     : Enum__Stack__Component__Status.DELETING,
                  'CREATION_FAILED': Enum__Stack__Component__Status.FAILED}

AMG_STATUS_MAP = {'ACTIVE'       : Enum__Stack__Component__Status.ACTIVE  ,        # AWS AMG uses a similar but independent set of status strings
                  'CREATING'     : Enum__Stack__Component__Status.CREATING,
                  'UPDATING'     : Enum__Stack__Component__Status.UPDATING,
                  'DELETING'     : Enum__Stack__Component__Status.DELETING,
                  'FAILED'       : Enum__Stack__Component__Status.FAILED  }


class Observability__AWS__Client(Type_Safe):                                        # Isolated boto3 + SigV4 boundary

    def amp_workspaces(self, region: str) -> Dict[str, Schema__Stack__Component__AMP]:
        out: Dict[str, Schema__Stack__Component__AMP] = {}
        try:                                                                        # Swallow region-wide errors (missing perms / empty account) — matches legacy behaviour
            from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
            from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
            amp   = Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
                service_name='amp', region=region or '')
            pages = amp.get_paginator('list_workspaces').paginate()
            for page in pages:
                for ws in page.get('workspaces', []):
                    alias            = ws.get('alias', ws['workspaceId'])
                    status_raw       = ws.get('status', {}).get('statusCode', '')
                    status           = AMP_STATUS_MAP.get(status_raw, Enum__Stack__Component__Status.UNKNOWN)
                    remote_write_url = self.amp_remote_write_url(region, ws['workspaceId'])
                    out[alias] = Schema__Stack__Component__AMP(workspace_id     = ws['workspaceId'],
                                                               alias            = alias             ,
                                                               status           = status            ,
                                                               remote_write_url = remote_write_url  )
        except Exception:
            pass
        return out

    def opensearch_domains(self, region: str) -> Dict[str, Schema__Stack__Component__OpenSearch]:
        out: Dict[str, Schema__Stack__Component__OpenSearch] = {}
        try:
            from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
            from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
            osc   = Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
                service_name='opensearch', region=region or '')
            names = [d['DomainName'] for d in osc.list_domain_names().get('DomainNames', [])]
            if not names:
                return out
            for ds in osc.describe_domains(DomainNames=names).get('DomainStatusList', []):
                endpoint = ds.get('Endpoint') or ds.get('Endpoints', {}).get('vpc', '') or ''
                status   = (Enum__Stack__Component__Status.PROCESSING if ds.get('Processing')
                            else Enum__Stack__Component__Status.ACTIVE)
                name     = ds['DomainName']
                out[name] = Schema__Stack__Component__OpenSearch(domain_name    = name                        ,
                                                                 engine_version = ds.get('EngineVersion', '') ,
                                                                 status         = status                     ,
                                                                 endpoint       = endpoint                   ,
                                                                 dashboards_url = f'https://{endpoint}/_dashboards' if endpoint else '',
                                                                 document_count = -1                         )  # Caller fills via opensearch_document_count()
        except Exception:
            pass
        return out

    def amg_workspaces(self, region: str) -> Dict[str, Schema__Stack__Component__Grafana]:
        out: Dict[str, Schema__Stack__Component__Grafana] = {}
        try:
            from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
            from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
            grafana = Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
                service_name='grafana', region=region or '')
            pages   = grafana.get_paginator('list_workspaces').paginate()
            for page in pages:
                for ws in page.get('workspaces', []):
                    status_raw = ws.get('status', '')
                    status     = AMG_STATUS_MAP.get(status_raw, Enum__Stack__Component__Status.UNKNOWN)
                    endpoint   = ws.get('endpoint', '') or ''
                    name       = ws['name']
                    out[name] = Schema__Stack__Component__Grafana(workspace_id = ws.get('id', '') ,
                                                                  name         = name             ,
                                                                  status       = status           ,
                                                                  endpoint     = endpoint         ,
                                                                  url          = f'https://{endpoint}' if endpoint else '')
        except Exception:
            pass
        return out

    def amp_delete_workspace(self, region: str, alias: str) -> Schema__Stack__Component__Delete__Result:
        result = Schema__Stack__Component__Delete__Result(kind = Enum__Stack__Component__Kind.AMP)
        try:
            from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
            from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
            amp        = Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
                service_name='amp', region=region or '')
            workspaces = amp.list_workspaces(alias=alias).get('workspaces', [])     # Aliased lookup — cheaper than paginating all
            if not workspaces:
                result.outcome = Enum__Component__Delete__Outcome.NOT_FOUND
                return result
            last_id = ''
            for ws in workspaces:
                amp.delete_workspace(workspaceId=ws['workspaceId'])
                last_id = ws['workspaceId']
            result.outcome     = Enum__Component__Delete__Outcome.DELETED
            result.resource_id = last_id                                            # Most-recent deleted id (single workspace in practice)
        except Exception as exc:
            result.outcome       = Enum__Component__Delete__Outcome.FAILED
            result.error_message = str(exc)
        return result

    def opensearch_delete_domain(self, region: str, domain_name: str) -> Schema__Stack__Component__Delete__Result:
        result = Schema__Stack__Component__Delete__Result(kind        = Enum__Stack__Component__Kind.OPENSEARCH,
                                                          resource_id = domain_name                            )
        try:
            from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
            from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
            osc = Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
                service_name='opensearch', region=region or '')
            try:
                osc.delete_domain(DomainName=domain_name)
                result.outcome = Enum__Component__Delete__Outcome.DELETED           # AWS returns immediately; the domain enters DELETING state for ~10 min
            except osc.exceptions.ResourceNotFoundException:
                result.outcome     = Enum__Component__Delete__Outcome.NOT_FOUND
                result.resource_id = ''                                             # Nothing matched — clear the id to avoid misleading callers
        except Exception as exc:
            result.outcome       = Enum__Component__Delete__Outcome.FAILED
            result.error_message = str(exc)
        return result

    def amg_delete_workspace(self, region: str, name: str) -> Schema__Stack__Component__Delete__Result:
        result = Schema__Stack__Component__Delete__Result(kind = Enum__Stack__Component__Kind.GRAFANA)
        try:
            from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
            from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
            grafana       = Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
                service_name='grafana', region=region or '')
            workspace_id  = ''
            for page in grafana.get_paginator('list_workspaces').paginate():        # AMG has no alias-lookup API; paginate to find by name
                for ws in page.get('workspaces', []):
                    if ws.get('name') == name:
                        workspace_id = ws.get('id', '')
                        break
                if workspace_id:
                    break
            if not workspace_id:
                result.outcome = Enum__Component__Delete__Outcome.NOT_FOUND
                return result
            grafana.delete_workspace(workspaceId=workspace_id)
            result.outcome     = Enum__Component__Delete__Outcome.DELETED
            result.resource_id = workspace_id
        except Exception as exc:
            result.outcome       = Enum__Component__Delete__Outcome.FAILED
            result.error_message = str(exc)
        return result

    def opensearch_document_count(self, endpoint: str, region: str, index: str) -> int:
        if not endpoint or not index:                                               # No endpoint yet (provisioning) — skip the round trip
            return -1
        try:
            response = self.sigv4_request('GET', f'https://{endpoint}/{index}/_count', region)
            if response.status_code == 200:
                return int(response.json().get('count', 0))
        except Exception:
            pass
        return -1

    def amp_remote_write_url(self, region: str, workspace_id: str) -> str:
        return (f'https://aps-workspaces.{region}.amazonaws.com'
                f'/workspaces/{workspace_id}/api/v1/remote_write')

    def sigv4_request(self, method: str, url: str, region: str,
                            body: bytes = b'', extra_headers: dict = None) -> requests.Response:
        session = boto3.Session()
        creds   = session.get_credentials()
        headers = {'Content-Type': 'application/json', **(extra_headers or {})}
        req     = AWSRequest(method=method.upper(), url=url, data=body, headers=headers)
        SigV4Auth(creds, 'es', region).add_auth(req)
        return requests.request(method, url, data=body, headers=dict(req.headers), timeout=60)

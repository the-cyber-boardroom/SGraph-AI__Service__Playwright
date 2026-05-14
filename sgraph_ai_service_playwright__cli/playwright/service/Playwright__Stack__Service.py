# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright__Stack__Service
# Tier-1 orchestrator for `sp playwright`. Launches ephemeral Playwright
# FastAPI instances as pods on a host, driving the host-plane pods API via
# Host_Plane__Client. Consumed by both the typer CLI (Tier 2A) and the
# FastAPI routes (Tier 2B).
#
# Backend: POD — one diniscruz/sg-playwright container per stack, started on
# a host control plane. The EC2-node backend and --with-mitmproxy are
# follow-ons (see team/roles/architect/reviews/05/14/
# v0.2.11__sp-playwright-spec-design.md §2, §9).
#
# Operations:
#   - create_stack(request, creator='')
#   - list_stacks(host_url, host_api_key)
#   - get_stack_info(host_url, host_api_key, stack_name)
#   - delete_stack(host_url, host_api_key, stack_name)
#   - health(host_url, host_api_key, stack_name)
#
# host_plane_client() is the seam unit tests override with an in-memory fake
# (no mocks — fakes are subclasses).
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.utils.Env                                                          import get_env

from sgraph_ai_service_playwright__cli.playwright.collections.List__Schema__Playwright__Stack__Info import List__Schema__Playwright__Stack__Info
from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State    import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Health      import Schema__Playwright__Health
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Create__Request  import Schema__Playwright__Stack__Create__Request
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Create__Response import Schema__Playwright__Stack__Create__Response
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Delete__Response import Schema__Playwright__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Info import Schema__Playwright__Stack__Info
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__List import Schema__Playwright__Stack__List
from sgraph_ai_service_playwright__cli.playwright.service.Host_Plane__Client          import Host_Plane__Client
from sgraph_ai_service_playwright__cli.playwright.service.Random__Stack__Name__Generator import Random__Stack__Name__Generator


DEFAULT_IMAGE                = 'diniscruz/sg-playwright'                             # Docker Hub image — the only thing a stack runs
TYPE_ID                      = 'playwright'                                         # host-plane pod tag — list/info/delete filter on this
POD_INTERNAL_PORT            = '8000/tcp'                                            # the port the Playwright FastAPI binds inside the container
ENV_VAR__HOST_PLANE_URL      = 'SG_PLAYWRIGHT__HOST_PLANE_URL'
ENV_VAR__HOST_PLANE_API_KEY  = 'SG_PLAYWRIGHT__HOST_PLANE_API_KEY'


class Playwright__Stack__Service(Type_Safe):

    def setup(self) -> 'Playwright__Stack__Service':                                # registry lifecycle hook — nothing to lazy-init for the POD backend
        return self

    # ── seam for tests — override to inject an in-memory fake ────────────────
    def host_plane_client(self, host_url: str, host_api_key: str) -> Host_Plane__Client:
        return Host_Plane__Client(base_url = self.resolve_host_url(host_url)        ,
                                  api_key  = self.resolve_host_api_key(host_api_key))

    # ── env-var fallbacks ────────────────────────────────────────────────────
    def resolve_host_url(self, host_url: str) -> str:
        return host_url or get_env(ENV_VAR__HOST_PLANE_URL, '')

    def resolve_host_api_key(self, host_api_key: str) -> str:
        return host_api_key or get_env(ENV_VAR__HOST_PLANE_API_KEY, '')

    # ── operations ───────────────────────────────────────────────────────────
    def create_stack(self, request : Schema__Playwright__Stack__Create__Request,
                            creator : str = ''                                  ) -> Schema__Playwright__Stack__Create__Response:
        stack_name = str(request.stack_name) or Random__Stack__Name__Generator().generate()
        image      = f'{DEFAULT_IMAGE}:{request.image_tag}'
        ports      = {POD_INTERNAL_PORT: str(request.host_port)}
        env        = {}
        if str(request.api_key):
            env['FAST_API__AUTH__API_KEY__VALUE'] = str(request.api_key)

        try:
            client = self.host_plane_client(str(request.host_url), str(request.host_api_key))
            result = client.start_pod(name=stack_name, image=image, ports=ports,
                                      env=env, type_id=TYPE_ID)
        except Exception as error:                                                  # host-plane unreachable / refused — surface in the response, not a 500
            return Schema__Playwright__Stack__Create__Response(stack_name = stack_name,
                                                               image      = image     ,
                                                               host_port  = request.host_port,
                                                               started    = False     ,
                                                               state      = Enum__Playwright__Stack__State.PENDING,
                                                               error      = str(error))

        started = bool(result.get('started'))
        return Schema__Playwright__Stack__Create__Response(
            stack_name   = stack_name                                               ,
            pod_name     = result.get('name'        , stack_name)                   ,
            container_id = result.get('container_id', ''        )                   ,
            image        = image                                                    ,
            host_port    = request.host_port                                        ,
            started      = started                                                  ,
            state        = Enum__Playwright__Stack__State.RUNNING if started
                           else Enum__Playwright__Stack__State.PENDING               ,
            error        = result.get('error', '')                                  )

    def list_stacks(self, host_url: str = '', host_api_key: str = '') -> Schema__Playwright__Stack__List:
        client = self.host_plane_client(host_url, host_api_key)
        stacks = List__Schema__Playwright__Stack__Info()
        for pod in client.list_pods():
            if pod.get('type_id') == TYPE_ID:
                stacks.append(self.pod_to_info(pod))
        return Schema__Playwright__Stack__List(host_url = self.resolve_host_url(host_url),
                                               stacks   = stacks                        )

    def get_stack_info(self, host_url: str, host_api_key: str,
                             stack_name: str) -> Optional[Schema__Playwright__Stack__Info]:
        client = self.host_plane_client(host_url, host_api_key)
        pod    = client.get_pod(stack_name)
        if pod is None or pod.get('type_id') != TYPE_ID:                            # not found, or not one of ours
            return None
        return self.pod_to_info(pod)

    def delete_stack(self, host_url: str, host_api_key: str,
                           stack_name: str) -> Schema__Playwright__Stack__Delete__Response:
        client = self.host_plane_client(host_url, host_api_key)
        pod    = client.get_pod(stack_name)
        if pod is None or pod.get('type_id') != TYPE_ID:                            # nothing of ours matched — caller maps to 404
            return Schema__Playwright__Stack__Delete__Response(removed=False)
        client.remove_pod(stack_name)
        return Schema__Playwright__Stack__Delete__Response(stack_name = stack_name,
                                                          pod_name   = stack_name,
                                                          removed    = True       )

    def health(self, host_url: str, host_api_key: str,
                     stack_name: str) -> Schema__Playwright__Health:
        try:
            client = self.host_plane_client(host_url, host_api_key)
            pod    = client.get_pod(stack_name)
        except Exception as error:
            return Schema__Playwright__Health(stack_name = stack_name,
                                              state      = Enum__Playwright__Stack__State.UNKNOWN,
                                              running    = False     ,
                                              error      = str(error))
        if pod is None or pod.get('type_id') != TYPE_ID:
            return Schema__Playwright__Health(stack_name = stack_name,
                                              state      = Enum__Playwright__Stack__State.UNKNOWN,
                                              running    = False     ,
                                              error      = f'no playwright stack matched {stack_name!r}')
        state = self.map_state(pod.get('status', ''))
        return Schema__Playwright__Health(stack_name = stack_name,
                                          state      = state     ,
                                          running    = state == Enum__Playwright__Stack__State.RUNNING)

    # ── pure mappers ─────────────────────────────────────────────────────────
    @staticmethod
    def map_state(status: str) -> Enum__Playwright__Stack__State:                   # host-plane status string → state enum
        mapping = {'running' : Enum__Playwright__Stack__State.RUNNING,
                   'exited'  : Enum__Playwright__Stack__State.EXITED ,
                   'created' : Enum__Playwright__Stack__State.PENDING,
                   'pending' : Enum__Playwright__Stack__State.PENDING}
        return mapping.get(str(status).lower(), Enum__Playwright__Stack__State.UNKNOWN)

    @staticmethod
    def extract_host_port(ports: dict) -> int:                                      # { "8000/tcp": [{"HostPort": "8000"}] } → 8000
        binding = (ports or {}).get(POD_INTERNAL_PORT)
        if isinstance(binding, list) and binding:
            try:
                return int(binding[0].get('HostPort', 0))
            except (ValueError, TypeError, AttributeError):
                return 0
        if isinstance(binding, str):                                                # { "8000/tcp": "8000" } compact form
            try:
                return int(binding)
            except ValueError:
                return 0
        return 0

    def pod_to_info(self, pod: dict) -> Schema__Playwright__Stack__Info:
        return Schema__Playwright__Stack__Info(
            stack_name = pod.get('name'      , '')                                  ,
            pod_name   = pod.get('name'      , '')                                  ,
            image      = pod.get('image'     , '')                                  ,
            state      = self.map_state(pod.get('status', ''))                      ,
            status     = pod.get('state'     , '')                                  ,
            host_port  = self.extract_host_port(pod.get('ports', {}))               ,
            created_at = pod.get('created_at', '')                                  )

# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — ALB__AWS__Client
# Sole boto3 boundary for Application Load Balancer operations.
# Covers load balancers, target groups, listeners, and target health.
#
# Credentials are resolved via Sg__Aws__Session.from_context() so that
# `sg credentials switch dev` is honoured by all ELBV2 calls.
# Subclasses override client() to inject fakes for unit tests.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

from botocore.exceptions import ClientError
from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.alb.collections.List__Schema__ALB__Listener               import List__Schema__ALB__Listener
from sgraph_ai_service_playwright__cli.aws.alb.collections.List__Schema__ALB__Load_Balancer           import List__Schema__ALB__Load_Balancer
from sgraph_ai_service_playwright__cli.aws.alb.collections.List__Schema__ALB__Target_Group            import List__Schema__ALB__Target_Group
from sgraph_ai_service_playwright__cli.aws.alb.collections.List__Schema__ALB__Target_Health_Description import List__Schema__ALB__Target_Health_Description
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__LB_Scheme                             import Enum__ALB__LB_Scheme
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__LB_State                              import Enum__ALB__LB_State
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Protocol                              import Enum__ALB__Protocol
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Target_Health                         import Enum__ALB__Target_Health
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Target_Type                           import Enum__ALB__Target_Type
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__LB_Arn                       import Safe_Str__ALB__LB_Arn
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__LB_Name                      import Safe_Str__ALB__LB_Name
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__Listener_Arn                 import Safe_Str__ALB__Listener_Arn
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__TG_Arn                       import Safe_Str__ALB__TG_Arn
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__TG_Name                      import Safe_Str__ALB__TG_Name
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Default_Action                    import Schema__ALB__Default_Action
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Listener                          import Schema__ALB__Listener
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Load_Balancer                     import Schema__ALB__Load_Balancer
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Target_Group                      import Schema__ALB__Target_Group
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Target_Health_Description         import Schema__ALB__Target_Health_Description
from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session                           import Sg__Aws__Session


_LB_NOT_FOUND_CODES  = {'LoadBalancerNotFound'}
_TG_NOT_FOUND_CODES  = {'TargetGroupNotFound'}
_LSN_NOT_FOUND_CODES = {'ListenerNotFound'}


class ALB__AWS__Client(Type_Safe):
    session : Sg__Aws__Session = None                                              # cached session — injected or lazy-init via setup()
    region  : str              = ''                                                # override to target a specific region

    def setup(self):                                                               # idempotent — noop if session already set
        if self.session is None:
            self.session = Sg__Aws__Session.from_context()
        return self

    def client(self):                                                              # single boto3 seam — subclass overrides for tests
        self.setup()
        return self.session.boto3_client_from_context('elbv2', region=self.region)

    def current_region(self) -> str:                                               # resolved region (explicit override → boto3 client meta)
        if self.region:
            return self.region
        try:
            meta = getattr(self.client(), 'meta', None)
            return getattr(meta, 'region_name', '') or ''
        except Exception:
            return ''

    # ── load balancer read ────────────────────────────────────────────────────

    def list_load_balancers(self) -> List__Schema__ALB__Load_Balancer:             # paginated via Marker/NextMarker
        elbv2  = self.client()
        raws   = []
        kwargs = {}
        while True:
            resp = elbv2.describe_load_balancers(**kwargs)
            raws.extend(resp.get('LoadBalancers', []))
            marker = resp.get('NextMarker')
            if not marker:
                break
            kwargs['Marker'] = marker
        result = List__Schema__ALB__Load_Balancer()
        for raw in raws:
            result.append(self._parse_load_balancer(raw))
        return result

    def describe_load_balancer(self, lb_arn_or_name: str) -> Optional[Schema__ALB__Load_Balancer]:
        try:
            if lb_arn_or_name.startswith('arn:'):
                resp = self.client().describe_load_balancers(LoadBalancerArns=[lb_arn_or_name])
            else:
                resp = self.client().describe_load_balancers(Names=[lb_arn_or_name])
            items = resp.get('LoadBalancers', [])
            if not items:
                return None
            return self._parse_load_balancer(items[0])
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in _LB_NOT_FOUND_CODES:
                return None
            raise

    # ── target group read ─────────────────────────────────────────────────────

    def list_target_groups(self, lb_arn: str = '') -> List__Schema__ALB__Target_Group:  # paginated via Marker/NextMarker
        elbv2  = self.client()
        raws   = []
        kwargs = {}
        if lb_arn:
            kwargs['LoadBalancerArn'] = lb_arn
        while True:
            resp = elbv2.describe_target_groups(**kwargs)
            raws.extend(resp.get('TargetGroups', []))
            marker = resp.get('NextMarker')
            if not marker:
                break
            kwargs['Marker'] = marker
        result = List__Schema__ALB__Target_Group()
        for raw in raws:
            result.append(self._parse_target_group(raw))
        return result

    def describe_target_group(self, tg_arn: str) -> Optional[Schema__ALB__Target_Group]:
        try:
            resp  = self.client().describe_target_groups(TargetGroupArns=[tg_arn])
            items = resp.get('TargetGroups', [])
            if not items:
                return None
            return self._parse_target_group(items[0])
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in _TG_NOT_FOUND_CODES:
                return None
            raise

    # ── listener read ─────────────────────────────────────────────────────────

    def list_listeners(self, lb_arn: str) -> List__Schema__ALB__Listener:         # paginated via NextMarker
        elbv2  = self.client()
        raws   = []
        kwargs = {'LoadBalancerArn': lb_arn}
        while True:
            resp = elbv2.describe_listeners(**kwargs)
            raws.extend(resp.get('Listeners', []))
            marker = resp.get('NextMarker')
            if not marker:
                break
            kwargs['Marker'] = marker
        result = List__Schema__ALB__Listener()
        for raw in raws:
            result.append(self._parse_listener(raw))
        return result

    def describe_listener(self, listener_arn: str) -> Optional[Schema__ALB__Listener]:
        try:
            resp  = self.client().describe_listeners(ListenerArns=[listener_arn])
            items = resp.get('Listeners', [])
            if not items:
                return None
            return self._parse_listener(items[0])
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in _LSN_NOT_FOUND_CODES:
                return None
            raise

    # ── target health read ────────────────────────────────────────────────────

    def describe_target_health(self, tg_arn: str) -> List__Schema__ALB__Target_Health_Description:
        resp  = self.client().describe_target_health(TargetGroupArn=tg_arn)
        items = resp.get('TargetHealthDescriptions', [])
        result = List__Schema__ALB__Target_Health_Description()
        for raw in items:
            result.append(self._parse_target_health(raw))
        return result

    # ── load balancer mutations ───────────────────────────────────────────────

    def create_load_balancer(self, name: str, subnets: list,
                              security_groups: list,
                              scheme: str = 'internet-facing',
                              tags: dict = None) -> Schema__ALB__Load_Balancer:
        tag_list = [{'Key': k, 'Value': v} for k, v in (tags or {}).items()]
        resp = self.client().create_load_balancer(
            Name           = name,
            Subnets        = subnets or [],
            SecurityGroups = security_groups or [],
            Scheme         = scheme,
            Type           = 'application',
            Tags           = tag_list,
        )
        items = resp.get('LoadBalancers', [])
        if not items:
            raise RuntimeError(f'create_load_balancer returned empty list for {name!r}')
        return self._parse_load_balancer(items[0])

    def delete_load_balancer(self, lb_arn: str) -> None:
        try:
            self.client().delete_load_balancer(LoadBalancerArn=lb_arn)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in _LB_NOT_FOUND_CODES:
                return
            raise

    def modify_load_balancer_attributes(self, lb_arn: str, attributes: list) -> None:
        self.client().modify_load_balancer_attributes(
            LoadBalancerArn = lb_arn,
            Attributes      = attributes,
        )

    def describe_load_balancer_attributes(self, lb_arn: str) -> list:
        resp = self.client().describe_load_balancer_attributes(LoadBalancerArn=lb_arn)
        return resp.get('Attributes', [])

    # ── target group mutations ────────────────────────────────────────────────

    def create_target_group(self, name: str, vpc_id: str,
                             protocol: str = 'HTTP',
                             port: int = 8080,
                             target_type: str = 'instance',
                             health_check_protocol: str = 'HTTP',
                             health_check_port: str = '8080',
                             health_check_path: str = '/info/health',
                             tags: dict = None) -> Schema__ALB__Target_Group:
        tag_list = [{'Key': k, 'Value': v} for k, v in (tags or {}).items()]
        resp = self.client().create_target_group(
            Name                = name,
            Protocol            = protocol,
            Port                = port,
            VpcId               = vpc_id,
            TargetType          = target_type,
            HealthCheckProtocol = health_check_protocol,
            HealthCheckPort     = health_check_port,
            HealthCheckPath     = health_check_path,
        )
        if tag_list:
            items = resp.get('TargetGroups', [])
            if items:
                tg_arn = items[0].get('TargetGroupArn', '')
                if tg_arn:
                    self.client().add_tags(ResourceArns=[tg_arn], Tags=tag_list)
        items = resp.get('TargetGroups', [])
        if not items:
            raise RuntimeError(f'create_target_group returned empty list for {name!r}')
        return self._parse_target_group(items[0])

    def delete_target_group(self, tg_arn: str) -> None:
        try:
            self.client().delete_target_group(TargetGroupArn=tg_arn)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in _TG_NOT_FOUND_CODES:
                return
            raise

    def modify_target_group(self, tg_arn: str, **kwargs) -> None:
        self.client().modify_target_group(TargetGroupArn=tg_arn, **kwargs)

    def register_targets(self, tg_arn: str, targets: list) -> None:
        self.client().register_targets(TargetGroupArn=tg_arn, Targets=targets)

    def deregister_targets(self, tg_arn: str, targets: list) -> None:
        self.client().deregister_targets(TargetGroupArn=tg_arn, Targets=targets)

    # ── listener mutations ────────────────────────────────────────────────────

    def create_listener(self, lb_arn: str, tg_arn: str,
                         protocol: str = 'HTTP',
                         port: int = 80) -> Schema__ALB__Listener:
        default_actions = [{'Type': 'forward', 'TargetGroupArn': tg_arn}]
        resp = self.client().create_listener(
            LoadBalancerArn = lb_arn,
            Protocol        = protocol,
            Port            = port,
            DefaultActions  = default_actions,
        )
        items = resp.get('Listeners', [])
        if not items:
            raise RuntimeError(f'create_listener returned empty list for lb {lb_arn!r}')
        return self._parse_listener(items[0])

    def delete_listener(self, listener_arn: str) -> None:
        try:
            self.client().delete_listener(ListenerArn=listener_arn)
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in _LSN_NOT_FOUND_CODES:
                return
            raise

    def modify_listener(self, listener_arn: str, **kwargs) -> None:
        self.client().modify_listener(ListenerArn=listener_arn, **kwargs)

    # ── tag mutations ─────────────────────────────────────────────────────────

    def add_tags(self, resource_arns: list, tags: dict) -> None:
        tag_list = [{'Key': k, 'Value': v} for k, v in tags.items()]
        self.client().add_tags(ResourceArns=resource_arns, Tags=tag_list)

    def remove_tags(self, resource_arns: list, tag_keys: list) -> None:
        self.client().remove_tags(ResourceArns=resource_arns, TagKeys=tag_keys)

    # ── internal ──────────────────────────────────────────────────────────────

    def _parse_load_balancer(self, raw: dict) -> Schema__ALB__Load_Balancer:
        raw_state = raw.get('State', {}).get('Code', 'unknown')
        try:
            state = Enum__ALB__LB_State(raw_state)
        except ValueError:
            state = Enum__ALB__LB_State.UNKNOWN
        raw_scheme = raw.get('Scheme', 'unknown')
        try:
            scheme = Enum__ALB__LB_Scheme(raw_scheme)
        except ValueError:
            scheme = Enum__ALB__LB_Scheme.UNKNOWN
        raw_tags = raw.get('Tags', [])                                             # populated when caller attaches tags list
        tags     = {t['Key']: t['Value'] for t in raw_tags if 'Key' in t}         # normalise AWS tag list to plain dict
        return Schema__ALB__Load_Balancer(
            lb_arn       = Safe_Str__ALB__LB_Arn(raw.get('LoadBalancerArn', '')),
            lb_name      = Safe_Str__ALB__LB_Name(raw.get('LoadBalancerName', '')),
            dns_name     = raw.get('DNSName', ''),
            state        = state,
            scheme       = scheme,
            vpc_id       = raw.get('VpcId', ''),
            created_time = str(raw.get('CreatedTime', '')) if raw.get('CreatedTime') else '',
            tags         = tags,
        )

    def _parse_target_group(self, raw: dict) -> Schema__ALB__Target_Group:
        raw_proto = raw.get('Protocol', 'unknown')
        try:
            protocol = Enum__ALB__Protocol(raw_proto)
        except ValueError:
            protocol = Enum__ALB__Protocol.UNKNOWN
        raw_type = raw.get('TargetType', 'instance')
        try:
            target_type = Enum__ALB__Target_Type(raw_type)
        except ValueError:
            target_type = Enum__ALB__Target_Type.INSTANCE
        raw_tags = raw.get('Tags', [])
        tags     = {t['Key']: t['Value'] for t in raw_tags if 'Key' in t}
        return Schema__ALB__Target_Group(
            tg_arn                = Safe_Str__ALB__TG_Arn(raw.get('TargetGroupArn', '')),
            tg_name               = Safe_Str__ALB__TG_Name(raw.get('TargetGroupName', '')),
            protocol              = protocol,
            port                  = int(raw.get('Port', 0)),
            vpc_id                = raw.get('VpcId', ''),
            target_type           = target_type,
            health_check_protocol = raw.get('HealthCheckProtocol', ''),
            health_check_port     = str(raw.get('HealthCheckPort', '')),
            health_check_path     = raw.get('HealthCheckPath', ''),
            tags                  = tags,
        )

    def _parse_listener(self, raw: dict) -> Schema__ALB__Listener:
        raw_proto = raw.get('Protocol', 'HTTP')
        try:
            protocol = Enum__ALB__Protocol(raw_proto)
        except ValueError:
            protocol = Enum__ALB__Protocol.UNKNOWN
        actions        = raw.get('DefaultActions', [])
        first_action   = actions[0] if actions else {}
        default_action = Schema__ALB__Default_Action(
            action_type = first_action.get('Type', ''),
            tg_arn      = Safe_Str__ALB__TG_Arn(first_action.get('TargetGroupArn', '')),
        )
        return Schema__ALB__Listener(
            listener_arn   = Safe_Str__ALB__Listener_Arn(raw.get('ListenerArn', '')),
            lb_arn         = Safe_Str__ALB__LB_Arn(raw.get('LoadBalancerArn', '')),
            protocol       = protocol,
            port           = int(raw.get('Port', 0)),
            default_action = default_action,
        )

    def _parse_target_health(self, raw: dict) -> Schema__ALB__Target_Health_Description:
        target      = raw.get('Target', {})
        health      = raw.get('TargetHealth', {})
        raw_state   = health.get('State', 'unknown')
        try:
            health_status = Enum__ALB__Target_Health(raw_state)
        except ValueError:
            health_status = Enum__ALB__Target_Health.UNKNOWN
        return Schema__ALB__Target_Health_Description(
            target_id     = target.get('Id', ''),
            target_port   = int(target.get('Port', 0)),
            health_status = health_status,
            reason_code   = health.get('Reason', ''),
            description   = health.get('Description', ''),
        )

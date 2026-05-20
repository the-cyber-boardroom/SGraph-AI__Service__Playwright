# ═══════════════════════════════════════════════════════════════════════════════
# Tests — ALB__AWS__Client__In_Memory
# Dict-backed fake boto3 ELBV2 client for unit tests.  No mocks. No patches.
# Subclasses ALB__AWS__Client and overrides client() to return _Fake_ELBV2.
# ═══════════════════════════════════════════════════════════════════════════════

import uuid

from botocore.exceptions import ClientError

from sgraph_ai_service_playwright__cli.aws.alb.service.ALB__AWS__Client import ALB__AWS__Client


def _client_error(code: str, message: str, operation: str) -> ClientError:
    return ClientError({'Error': {'Code': code, 'Message': message}}, operation)


class _Fake_ELBV2_Client:
    """Minimal boto3-alike ELBV2 client backed by in-memory dicts."""

    def __init__(self, lbs: dict, tgs: dict, listeners: dict,
                 target_health: dict, lb_tags: dict, tg_tags: dict,
                 listener_tags: dict):
        self._lbs           = lbs            # lb_arn → raw lb dict
        self._tgs           = tgs            # tg_arn → raw tg dict
        self._listeners     = listeners      # listener_arn → raw listener dict
        self._target_health = target_health  # tg_arn → [list of target health dicts]
        self._lb_tags       = lb_tags        # lb_arn → [tag dicts]
        self._tg_tags       = tg_tags        # tg_arn → [tag dicts]
        self._listener_tags = listener_tags  # listener_arn → [tag dicts]
        self._targets       = {}             # tg_arn → {target_id → target_spec}

    # ── load balancers ────────────────────────────────────────────────────────

    def describe_load_balancers(self, LoadBalancerArns=None, Names=None,
                                 Marker=None, PageSize=None, **kwargs):
        items = list(self._lbs.values())
        if LoadBalancerArns:
            items = [lb for lb in items if lb['LoadBalancerArn'] in LoadBalancerArns]
            if not items and LoadBalancerArns:
                raise _client_error('LoadBalancerNotFound',
                                     f'LB not found: {LoadBalancerArns}',
                                     'DescribeLoadBalancers')
        if Names:
            items = [lb for lb in items if lb['LoadBalancerName'] in Names]
            if not items and Names:
                raise _client_error('LoadBalancerNotFound',
                                     f'LB not found: {Names}',
                                     'DescribeLoadBalancers')
        for lb in items:                                                           # attach tags to raw dict
            lb['Tags'] = self._lb_tags.get(lb['LoadBalancerArn'], [])
        return {'LoadBalancers': items}

    def create_load_balancer(self, Name, Subnets, SecurityGroups, Scheme,
                              Type, Tags=None, **kwargs):
        lb_arn = f'arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/{Name}/{uuid.uuid4().hex[:16]}'
        raw    = {
            'LoadBalancerArn'  : lb_arn,
            'LoadBalancerName' : Name,
            'DNSName'          : f'{Name}.us-east-1.elb.amazonaws.com',
            'State'            : {'Code': 'active'},
            'Scheme'           : Scheme,
            'VpcId'            : 'vpc-00000000',
            'Type'             : Type,
            'CreatedTime'      : '2026-05-19T00:00:00Z',
            'Tags'             : Tags or [],
        }
        self._lbs[lb_arn] = raw
        if Tags:
            self._lb_tags[lb_arn] = Tags
        return {'LoadBalancers': [raw]}

    def delete_load_balancer(self, LoadBalancerArn, **kwargs):
        self._lbs.pop(LoadBalancerArn, None)
        self._lb_tags.pop(LoadBalancerArn, None)
        return {}

    def modify_load_balancer_attributes(self, LoadBalancerArn, Attributes, **kwargs):
        return {'Attributes': Attributes}

    def describe_load_balancer_attributes(self, LoadBalancerArn, **kwargs):
        return {'Attributes': []}

    # ── target groups ─────────────────────────────────────────────────────────

    def describe_target_groups(self, TargetGroupArns=None, LoadBalancerArn=None,
                                Names=None, Marker=None, **kwargs):
        items = list(self._tgs.values())
        if TargetGroupArns:
            items = [tg for tg in items if tg['TargetGroupArn'] in TargetGroupArns]
            if not items and TargetGroupArns:
                raise _client_error('TargetGroupNotFound',
                                     f'TG not found: {TargetGroupArns}',
                                     'DescribeTargetGroups')
        if Names:
            items = [tg for tg in items if tg['TargetGroupName'] in Names]
        for tg in items:
            tg['Tags'] = self._tg_tags.get(tg['TargetGroupArn'], [])
        return {'TargetGroups': items}

    def create_target_group(self, Name, Protocol, Port, VpcId, TargetType,
                             HealthCheckProtocol, HealthCheckPort, HealthCheckPath,
                             **kwargs):
        tg_arn = f'arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/{Name}/{uuid.uuid4().hex[:16]}'
        raw    = {
            'TargetGroupArn'      : tg_arn,
            'TargetGroupName'     : Name,
            'Protocol'            : Protocol,
            'Port'                : Port,
            'VpcId'               : VpcId,
            'TargetType'          : TargetType,
            'HealthCheckProtocol' : HealthCheckProtocol,
            'HealthCheckPort'     : HealthCheckPort,
            'HealthCheckPath'     : HealthCheckPath,
            'Tags'                : [],
        }
        self._tgs[tg_arn] = raw
        self._target_health[tg_arn] = []
        self._targets[tg_arn]       = {}
        return {'TargetGroups': [raw]}

    def delete_target_group(self, TargetGroupArn, **kwargs):
        self._tgs.pop(TargetGroupArn, None)
        self._tg_tags.pop(TargetGroupArn, None)
        self._target_health.pop(TargetGroupArn, None)
        self._targets.pop(TargetGroupArn, None)
        return {}

    def modify_target_group(self, TargetGroupArn, **kwargs):
        return {}

    def register_targets(self, TargetGroupArn, Targets, **kwargs):
        if TargetGroupArn not in self._targets:
            self._targets[TargetGroupArn] = {}
        for target in Targets:
            target_id = target.get('Id', '')
            port      = target.get('Port', 0)
            self._targets[TargetGroupArn][target_id] = target
            # also add to target health
            if TargetGroupArn not in self._target_health:
                self._target_health[TargetGroupArn] = []
            self._target_health[TargetGroupArn].append({
                'Target'      : {'Id': target_id, 'Port': port},
                'TargetHealth': {'State': 'initial'},
            })
        return {}

    def deregister_targets(self, TargetGroupArn, Targets, **kwargs):
        if TargetGroupArn in self._targets:
            for target in Targets:
                self._targets[TargetGroupArn].pop(target.get('Id', ''), None)
        if TargetGroupArn in self._target_health:
            ids_to_remove = {t.get('Id', '') for t in Targets}
            self._target_health[TargetGroupArn] = [
                h for h in self._target_health[TargetGroupArn]
                if h.get('Target', {}).get('Id', '') not in ids_to_remove
            ]
        return {}

    # ── listeners ─────────────────────────────────────────────────────────────

    def describe_listeners(self, LoadBalancerArn=None, ListenerArns=None,
                            Marker=None, **kwargs):
        items = list(self._listeners.values())
        if LoadBalancerArn:
            items = [l for l in items if l.get('LoadBalancerArn') == LoadBalancerArn]
        if ListenerArns:
            items = [l for l in items if l['ListenerArn'] in ListenerArns]
            if not items and ListenerArns:
                raise _client_error('ListenerNotFound',
                                     f'Listener not found: {ListenerArns}',
                                     'DescribeListeners')
        return {'Listeners': items}

    def create_listener(self, LoadBalancerArn, Protocol, Port, DefaultActions,
                         **kwargs):
        listener_arn = f'arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/{uuid.uuid4().hex[:16]}'
        raw          = {
            'ListenerArn'    : listener_arn,
            'LoadBalancerArn': LoadBalancerArn,
            'Protocol'       : Protocol,
            'Port'           : Port,
            'DefaultActions' : DefaultActions or [],
        }
        self._listeners[listener_arn] = raw
        return {'Listeners': [raw]}

    def delete_listener(self, ListenerArn, **kwargs):
        self._listeners.pop(ListenerArn, None)
        self._listener_tags.pop(ListenerArn, None)
        return {}

    def modify_listener(self, ListenerArn, **kwargs):
        return {}

    # ── target health ─────────────────────────────────────────────────────────

    def describe_target_health(self, TargetGroupArn, Targets=None, **kwargs):
        items = self._target_health.get(TargetGroupArn, [])
        return {'TargetHealthDescriptions': items}

    # ── tags ──────────────────────────────────────────────────────────────────

    def add_tags(self, ResourceArns, Tags, **kwargs):
        for arn in ResourceArns:
            if arn in self._lbs:
                existing = {t['Key']: t for t in self._lb_tags.get(arn, [])}
                for tag in Tags:
                    existing[tag['Key']] = tag
                self._lb_tags[arn] = list(existing.values())
                self._lbs[arn]['Tags'] = self._lb_tags[arn]
            elif arn in self._tgs:
                existing = {t['Key']: t for t in self._tg_tags.get(arn, [])}
                for tag in Tags:
                    existing[tag['Key']] = tag
                self._tg_tags[arn] = list(existing.values())
                self._tgs[arn]['Tags'] = self._tg_tags[arn]
            elif arn in self._listeners:
                existing = {t['Key']: t for t in self._listener_tags.get(arn, [])}
                for tag in Tags:
                    existing[tag['Key']] = tag
                self._listener_tags[arn] = list(existing.values())
        return {}

    def remove_tags(self, ResourceArns, TagKeys, **kwargs):
        for arn in ResourceArns:
            store = None
            if arn in self._lbs:
                store = self._lb_tags
            elif arn in self._tgs:
                store = self._tg_tags
            elif arn in self._listeners:
                store = self._listener_tags
            if store is not None:
                store[arn] = [t for t in store.get(arn, []) if t['Key'] not in TagKeys]
        return {}


class ALB__AWS__Client__In_Memory(ALB__AWS__Client):

    def __init__(self):
        super().__init__()
        self._lbs           = {}
        self._tgs           = {}
        self._listeners     = {}
        self._target_health = {}
        self._lb_tags       = {}
        self._tg_tags       = {}
        self._listener_tags = {}
        self._targets       = {}                                                    # tg_arn → {target_id → target_spec}
        self._fake          = _Fake_ELBV2_Client(
            lbs           = self._lbs,
            tgs           = self._tgs,
            listeners     = self._listeners,
            target_health = self._target_health,
            lb_tags       = self._lb_tags,
            tg_tags       = self._tg_tags,
            listener_tags = self._listener_tags,
        )
        self._fake._targets = self._targets                                         # share reference so register/deregister are visible
        self._region = 'us-east-1'

    def client(self):
        return self._fake

    def current_region(self) -> str:
        return self._region

    # ── test helpers ──────────────────────────────────────────────────────────

    def seed_load_balancer(self, name: str, scheme: str = 'internet-facing',
                            tags: dict = None) -> str:
        lb_arn = f'arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/{name}/seed0000'
        tag_list = [{'Key': k, 'Value': v} for k, v in (tags or {}).items()]
        self._lbs[lb_arn] = {
            'LoadBalancerArn'  : lb_arn,
            'LoadBalancerName' : name,
            'DNSName'          : f'{name}.us-east-1.elb.amazonaws.com',
            'State'            : {'Code': 'active'},
            'Scheme'           : scheme,
            'VpcId'            : 'vpc-seed0000',
            'Type'             : 'application',
            'CreatedTime'      : '2026-05-19T00:00:00Z',
            'Tags'             : tag_list,
        }
        if tag_list:
            self._lb_tags[lb_arn] = tag_list
        return lb_arn

    def seed_target_group(self, name: str, vpc_id: str = 'vpc-seed0000',
                           port: int = 8080, tags: dict = None) -> str:
        tg_arn = f'arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/{name}/seed0000'
        tag_list = [{'Key': k, 'Value': v} for k, v in (tags or {}).items()]
        self._tgs[tg_arn] = {
            'TargetGroupArn'      : tg_arn,
            'TargetGroupName'     : name,
            'Protocol'            : 'HTTP',
            'Port'                : port,
            'VpcId'               : vpc_id,
            'TargetType'          : 'instance',
            'HealthCheckProtocol' : 'HTTP',
            'HealthCheckPort'     : str(port),
            'HealthCheckPath'     : '/info/health',
            'Tags'                : tag_list,
        }
        self._target_health[tg_arn] = []
        self._targets[tg_arn]       = {}
        if tag_list:
            self._tg_tags[tg_arn] = tag_list
        return tg_arn

    def seed_listener(self, lb_arn: str, tg_arn: str, port: int = 80) -> str:
        listener_arn = f'arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/seed/{uuid.uuid4().hex[:16]}'
        self._listeners[listener_arn] = {
            'ListenerArn'    : listener_arn,
            'LoadBalancerArn': lb_arn,
            'Protocol'       : 'HTTP',
            'Port'           : port,
            'DefaultActions' : [{'Type': 'forward', 'TargetGroupArn': tg_arn}],
        }
        return listener_arn

    def seed_target_health(self, tg_arn: str, target_id: str,
                            state: str = 'healthy') -> None:
        if tg_arn not in self._target_health:
            self._target_health[tg_arn] = []
        self._target_health[tg_arn].append({
            'Target'      : {'Id': target_id, 'Port': 8080},
            'TargetHealth': {'State': state},
        })

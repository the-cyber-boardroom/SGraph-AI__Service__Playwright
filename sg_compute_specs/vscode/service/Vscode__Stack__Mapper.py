# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__Stack__Mapper
# Maps a raw boto3 DescribeInstances dict → Schema__Vscode__Info.
# Builds the ready-to-paste SSM port-forward + interactive-session commands.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__Stack__Mapper import (tag_value      ,
                                                                  state_str     ,
                                                                  uptime_seconds,
                                                                  first_sg_id   )
from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder import TAG_STACK_NAME
from sg_compute_specs.vscode.schemas.Schema__Vscode__Info import Schema__Vscode__Info

TAG_DISTRIBUTION = 'StackDistribution'
TAG_INGRESS      = 'StackIngress'
TAG_FQDN         = 'StackFqdn'
TAG_TERMINATE_AT = 'TerminateAt'
STACK_TYPE       = 'vscode'

EDITOR_PORT      = 8443                # instance-side port code-server is published on (127.0.0.1:8443 → container:8080)
INGRESS_PUBLIC   = 'public-https'      # mirrors Enum__Vscode__Ingress.PUBLIC_HTTPS.value


def _time_remaining(details: dict) -> tuple:
    raw = tag_value(details, TAG_TERMINATE_AT) or ''
    if not raw:
        return '', 0
    try:
        t         = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        remaining = int((t - datetime.now(timezone.utc)).total_seconds())
        return raw, max(0, remaining)
    except Exception:
        return raw, 0


def ssm_forward_command(instance_id: str, region: str, port: int = EDITOR_PORT) -> str:
    if not instance_id:
        return ''
    return (f'aws ssm start-session --target {instance_id} '
            f'--document-name AWS-StartPortForwardingSession '
            f'--parameters \'{{"portNumber":["{port}"],'
            f'"localPortNumber":["{port}"]}}\' '
            f'--region {region}')


def ssm_session_command(instance_id: str, region: str) -> str:
    if not instance_id:
        return ''
    return f'aws ssm start-session --target {instance_id} --region {region}'


def vscode_url_for(ingress: str, public_ip: str, fqdn: str = '', port: int = EDITOR_PORT) -> str:
    if ingress == INGRESS_PUBLIC:
        host = fqdn or public_ip                   # prefer the hostname (matches the LE cert SAN)
        if host:
            return f'https://{host}'
    return f'http://localhost:{port}'              # SSM-forward default — open after `sg vscode forward`


class Vscode__Stack__Mapper(Type_Safe):

    def to_info(self, details: dict, region: str) -> Schema__Vscode__Info:
        instance_id             = details.get('InstanceId', '') or ''
        public_ip               = details.get('PublicIpAddress', '') or ''
        ingress                 = tag_value(details, TAG_INGRESS) or 'ssm-forward'
        fqdn                    = tag_value(details, TAG_FQDN) or ''
        terminate_at, remaining = _time_remaining(details)
        return Schema__Vscode__Info(
            instance_id        = instance_id                                  ,
            stack_name         = tag_value(details, TAG_STACK_NAME)           ,
            region             = region                                       ,
            state              = state_str(details)                           ,
            public_ip          = public_ip                                    ,
            private_ip         = details.get('PrivateIpAddress', '') or ''    ,
            instance_type      = details.get('InstanceType', '')              ,
            ami_id             = details.get('ImageId', '')                   ,
            security_group_id  = first_sg_id(details)                         ,
            distribution       = tag_value(details, TAG_DISTRIBUTION)         ,
            ingress            = ingress                                      ,
            fqdn               = fqdn                                         ,
            vscode_url         = vscode_url_for(ingress, public_ip, fqdn)     ,
            ssm_forward        = ssm_forward_command(instance_id, region)     ,
            ssm_session        = ssm_session_command(instance_id, region)     ,
            uptime_seconds     = uptime_seconds(details)                      ,
            spot               = details.get('InstanceLifecycle', '') == 'spot',
            terminate_at       = terminate_at                                 ,
            time_remaining_sec = remaining                                    ,
        )

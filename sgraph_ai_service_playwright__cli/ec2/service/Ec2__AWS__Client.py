# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Ec2__AWS__Client
# Central AWS boundary for the Playwright EC2 stack — mirrors the
# Elastic__AWS__Client pattern used by `sp el`. Owns:
#   - Module-level pure helpers (random_deploy_name, get_creator,
#     uptime_str, instance_tag, instance_deploy_name) — no AWS calls,
#     no EC2 client. Called by both this module's class methods and by
#     scripts.provision_ec2's typer commands.
#   - The Ec2__AWS__Client class itself — every AWS-touching lookup /
#     mutation that the Playwright EC2 stack needs (find / resolve /
#     terminate). Keeps the boto3 surface narrow so the rest of the CLI
#     can stay pure Python + Type_Safe.
#
# Tag convention (mirrors scripts.provision_ec2):
#   sg:service        : 'playwright-ec2'   ← immutable; find_instances filters on this
#   sg:deploy-name    : '<adjective>-<scientist>'
#   sg:creator        : git email or $USER
#   sg:api-key-name   : header name
#   sg:api-key-value  : key value
#   sg:instance-type  : type at create time
#   stage             : 'dev' (default)
#
# Plan reference: team/comms/plans/v0.1.96__playwright-stack-split__02__api-consolidation.md
# (Phase A step 3a — naming + lookup helpers).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import secrets
import subprocess
from datetime                                                                       import datetime, timezone
from typing                                                                         import Optional

from osbot_aws.AWS_Config                                                           import AWS_Config
from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base import IMAGE_NAME as PLAYWRIGHT_IMAGE_NAME
from agent_mitmproxy.docker.Docker__Agent_Mitmproxy__Base                            import IMAGE_NAME as SIDECAR_IMAGE_NAME


TAG__SERVICE_KEY      = 'sg:service'                                                # Immutable identifier — find_instances filters on this, not Name (Name is user-editable in console)
TAG__SERVICE_VALUE    = 'playwright-ec2'
TAG__DEPLOY_NAME_KEY  = 'sg:deploy-name'                                            # Random two-word name; used by connect/delete/exec for human-friendly targeting

INSTANCE_STATES_LIVE  = ['pending', 'running', 'stopping', 'stopped']               # Terminated/shutting-down excluded from list operations


_ADJECTIVES = ['bold','bright','calm','clever','cool','daring','deep','eager',
               'fast','fierce','fresh','grand','happy','keen','light','lucky',
               'mellow','neat','quick','quiet','sharp','sleek','smart','swift','witty']
_SCIENTISTS = ['bohr','curie','darwin','dirac','einstein','euler','faraday',
               'fermi','feynman','galileo','gauss','hopper','hubble','lovelace',
               'maxwell','newton','noether','pascal','planck','turing','tesla',
               'volta','watt','wien','zeno']


def random_deploy_name() -> str:                                                    # 'happy-turing' / 'bold-curie' / ... — used as sg:deploy-name tag
    return f'{secrets.choice(_ADJECTIVES)}-{secrets.choice(_SCIENTISTS)}'


def get_creator() -> str:                                                           # Best-effort creator identity — git email if set, else $USER, else 'unknown'
    try:
        return subprocess.check_output(['git', 'config', 'user.email'],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return os.environ.get('USER', 'unknown')


def uptime_str(launch_time) -> str:                                                 # Render launch_time as 'Nd Nh' / 'Nh Nm' / 'Nm'; '?' on missing or malformed input
    if not launch_time:
        return '?'
    if not isinstance(launch_time, datetime):
        return '?'
    lt   = launch_time if launch_time.tzinfo else launch_time.replace(tzinfo=timezone.utc)
    secs = int((datetime.now(timezone.utc) - lt).total_seconds())
    if secs < 0:
        return '?'
    days, rem  = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins       = rem // 60
    if days:
        return f'{days}d {hours}h'
    if hours:
        return f'{hours}h {mins}m'
    return f'{mins}m'


def instance_tag(details: dict, key: str) -> str:                                   # Lowercase 'tags' key matches osbot-aws's instances_details() output
    for tag in details.get('tags', []):
        if tag.get('Key') == key:
            return tag.get('Value', '')
    return ''


def instance_deploy_name(details: dict) -> str:                                     # Convenience wrapper — the sg:deploy-name tag is the human-facing identifier
    return instance_tag(details, TAG__DEPLOY_NAME_KEY)


# ── AWS context accessors (Phase A step 3b) ─────────────────────────────────────
# Pure-data accessors over osbot_aws.AWS_Config — kept as module-level functions
# (no EC2 client needed). Each AWS_Config() call uses osbot_aws's auth caching.

def aws_account_id() -> str:
    return AWS_Config().aws_session_account_id()


def aws_region() -> str:
    return AWS_Config().aws_session_region_name()


def ecr_registry_host() -> str:                                                     # <account>.dkr.ecr.<region>.amazonaws.com — the host portion of every ECR URI
    return f'{aws_account_id()}.dkr.ecr.{aws_region()}.amazonaws.com'


def default_playwright_image_uri() -> str:                                          # Resolves to {registry}/{IMAGE_NAME}:latest at call time
    return f'{ecr_registry_host()}/{PLAYWRIGHT_IMAGE_NAME}:latest'


def default_sidecar_image_uri() -> str:
    return f'{ecr_registry_host()}/{SIDECAR_IMAGE_NAME}:latest'


class Ec2__AWS__Client(Type_Safe):                                                  # Narrow boto3 boundary for the Playwright EC2 stack

    def ec2(self):                                                                  # Single seam — tests override to return a fake EC2
        from osbot_aws.aws.ec2.EC2                                                  import EC2
        return EC2()

    def find_instances(self) -> dict:                                               # Every tagged playwright-ec2 instance in the live states (excludes terminated)
        ec2     = self.ec2()
        filters = [{'Name': f'tag:{TAG__SERVICE_KEY}', 'Values': [TAG__SERVICE_VALUE]},
                   {'Name': 'instance-state-name'    , 'Values': INSTANCE_STATES_LIVE}]
        return ec2.instances_details(filters=filters) or {}

    def find_instance_ids(self) -> list:
        return list(self.find_instances().keys())

    def resolve_instance_id(self, target: str) -> str:                              # Accept i-XXX or a deploy-name; raises ValueError on miss
        if target.startswith('i-'):
            return target
        for iid, details in self.find_instances().items():
            if instance_deploy_name(details) == target:
                return iid
        raise ValueError(f'No instance found with deploy-name {target!r}')

    def terminate_instances(self, nickname: Optional[str] = '') -> list:            # nickname='' → terminate ALL playwright-ec2 instances; otherwise only the one matching deploy-name
        instances = self.find_instances()
        to_kill   = [iid for iid, d in instances.items()
                     if not nickname or instance_deploy_name(d) == nickname]
        ec2 = self.ec2()
        for iid in to_kill:
            ec2.instance_terminate(iid)
        return to_kill

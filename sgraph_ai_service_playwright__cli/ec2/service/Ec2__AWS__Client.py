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

import json
import os
import secrets
import subprocess
import time
from datetime                                                                       import datetime, timezone
from typing                                                                         import Optional

from osbot_aws.AWS_Config                                                           import AWS_Config
from osbot_aws.aws.iam.IAM_Role                                                     import IAM_Role
from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

PLAYWRIGHT_IMAGE_NAME = 'diniscruz/sg-playwright'                                       # Docker Hub image (moved from ECR docker base class)
from sg_compute_specs.mitmproxy.docker.Docker__Agent_Mitmproxy__Base                 import IMAGE_NAME as SIDECAR_IMAGE_NAME


TAG__SERVICE_KEY      = 'sg:service'                                                # Immutable identifier — find_instances filters on this, not Name (Name is user-editable in console)
TAG__SERVICE_VALUE    = 'playwright-ec2'
TAG__DEPLOY_NAME_KEY  = 'sg:deploy-name'                                            # Random two-word name; used by connect/delete/exec for human-friendly targeting
TAG__AMI_STATUS_KEY   = 'sg:ami-status'                                             # untested | healthy | unhealthy

INSTANCE_STATES_LIVE  = ['pending', 'running', 'stopping', 'stopped']               # Terminated/shutting-down excluded from list operations

# Security group + AMI constants (Phase A step 3d)
SG__NAME                   = 'playwright-ec2'                                       # AWS reserves 'sg-*' prefix for SG IDs only — not for GroupName
SG__DESCRIPTION            = 'SG Playwright EC2 stack - ingress :8000 (Playwright API) + :8001 (sidecar admin) + :19009 (host control plane) - all API-key gated'    # ASCII only — AWS rejects multi-byte GroupDescription.

EC2__AMI_OWNER_AMAZON      = 'amazon'
EC2__AMI_NAME_AL2023       = 'al2023-ami-2023.*-x86_64'

EC2__PLAYWRIGHT_PORT       = 8000                                                   # Playwright API — exposed to the world via SG
EC2__SIDECAR_ADMIN_PORT    = 8001                                                   # Sidecar admin API — exposed via SG, API-key gated
EC2__HOST_CONTROL_PORT     = 19009                                                   # Host control plane (Fast_API__Host__Control) — API-key gated
# EC2__BROWSER_INTERNAL_PORT (3000) removed in Phase D — last consumer
# (sp forward-browser) deleted in the same commit. KasmVNC now lives in sp vnc.

SG_INGRESS_PORTS           = (EC2__PLAYWRIGHT_PORT, EC2__SIDECAR_ADMIN_PORT, EC2__HOST_CONTROL_PORT)


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

def aws_account_id() -> str:                                                        # cached via sg credentials store; STS fallback when no sg role active
    from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session import Sg__Aws__Session
    cached = Sg__Aws__Session.account_id_from_context()
    return cached or AWS_Config().aws_session_account_id()


def aws_region() -> str:
    return AWS_Config().aws_session_region_name()


def ecr_registry_host() -> str:                                                     # <account>.dkr.ecr.<region>.amazonaws.com — the host portion of every ECR URI
    return f'{aws_account_id()}.dkr.ecr.{aws_region()}.amazonaws.com'


def default_playwright_image_uri() -> str:                                          # Resolves to {registry}/{IMAGE_NAME}:latest at call time
    return f'{ecr_registry_host()}/{PLAYWRIGHT_IMAGE_NAME}:latest'


def default_sidecar_image_uri() -> str:
    return f'{ecr_registry_host()}/{SIDECAR_IMAGE_NAME}:latest'


# ── IAM (Phase A step 3c) ───────────────────────────────────────────────────────
# IAM role + instance profile + caller PassRole helpers. Kept as module-level
# functions matching the existing scripts/provision_ec2 surface so the typer
# commands and tests can keep importing under the same names. AWS reserves
# 'sg-*' for SG IDs only — the role/profile name 'playwright-ec2' is unaffected.

IAM__ROLE_NAME                 = 'playwright-ec2'                                   # AWS reserves 'sg-*' prefix for SG IDs only — applies to SG names, IAM instance profiles, and resource tags
IAM__ECR_READONLY_POLICY_ARN   = 'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly'
IAM__SSM_CORE_POLICY_ARN       = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'   # SSM session manager — no SSH needed
IAM__POLICY_ARNS               = (IAM__ECR_READONLY_POLICY_ARN, IAM__SSM_CORE_POLICY_ARN)
IAM__PROMETHEUS_RW_POLICY_ARN  = 'arn:aws:iam::aws:policy/AmazonPrometheusRemoteWriteAccess'
IAM__OBSERVABILITY_POLICY_ARNS = (IAM__PROMETHEUS_RW_POLICY_ARN,)                   # OpenSearch write access is domain-specific — added via resource policy. Phase C will move/strip this once observability moves to its own section.
IAM__ASSUME_ROLE_SERVICE       = 'ec2.amazonaws.com'
IAM__PASSROLE_POLICY_NAME      = 'sg-playwright-passrole-ec2'
IAM__STOP_INSTANCES_POLICY_NAME = 'sg-playwright-stop-vault-app'  # inline policy granting ec2:StopInstances on vault-app-tagged instances only


def decode_aws_auth_error(exc: Exception) -> str:                                   # Decodes the AWS-encoded "authorization failure" blob via sts:DecodeAuthorizationMessage
    import boto3, re
    msg = str(exc)
    if 'Encoded authorization failure message:' not in msg:
        return ''
    match = re.search(r'Encoded authorization failure message:\s*(\S+)', msg)
    if not match:
        return ''
    encoded = match.group(1)
    try:
        decoded = boto3.client('sts').decode_authorization_message(EncodedMessage=encoded)
        return decoded.get('DecodedMessage', '')
    except Exception:
        return ''


def ensure_caller_passrole(account: str) -> dict:                                   # Attach minimal iam:PassRole inline policy to the calling IAM user
    import boto3                                                                    # Lazy — only the typer command path needs sts/iam clients

    role_arn   = f'arn:aws:iam::{account}:role/{IAM__ROLE_NAME}'
    policy_doc = json.dumps({                                                       # Resource pinned to the playwright-ec2 role only; condition prevents cross-service abuse
        'Version'  : '2012-10-17',
        'Statement': [{'Sid'      : 'PassRoleToEC2Only'                       ,
                       'Effect'   : 'Allow'                                    ,
                       'Action'   : 'iam:PassRole'                             ,
                       'Resource' : role_arn                                   ,
                       'Condition': {'StringEquals': {'iam:PassedToService': 'ec2.amazonaws.com'}}}],
    })

    sts      = boto3.client('sts')
    identity = sts.get_caller_identity()
    arn      = identity.get('Arn', '')

    if ':user/' not in arn:                                                         # Federated / role principals can't have inline user policies — nothing to do
        return {'ok': False, 'action': 'skipped',
                'detail': f'Caller is not an IAM user ({arn}) — attach the policy manually in the console.'}

    username = arn.split(':user/')[-1]
    iam      = boto3.client('iam')

    existing = iam.list_user_policies(UserName=username).get('PolicyNames', [])
    if IAM__PASSROLE_POLICY_NAME in existing:
        return {'ok': True, 'action': 'already_exists',
                'detail': f'Policy {IAM__PASSROLE_POLICY_NAME!r} already attached to {username}.'}

    iam.put_user_policy(UserName=username, PolicyName=IAM__PASSROLE_POLICY_NAME, PolicyDocument=policy_doc)
    return {'ok': True, 'action': 'created',
            'detail': f'Attached inline policy {IAM__PASSROLE_POLICY_NAME!r} to {username} (PassRole → {role_arn}, EC2 only).'}


def ensure_stop_instances_policy() -> dict:                                         # Idempotent inline policy: allow ec2:StopInstances on vault-app-tagged instances only
    import boto3
    policy_doc = json.dumps({
        'Version'  : '2012-10-17',
        'Statement': [{'Sid'      : 'StopVaultAppInstances'                ,
                       'Effect'   : 'Allow'                                ,
                       'Action'   : 'ec2:StopInstances'                    ,
                       'Resource' : 'arn:aws:ec2:*:*:instance/*'           ,
                       'Condition': {'StringEquals': {'aws:ResourceTag/StackType': 'vault-app'}}}],
    })
    iam = boto3.client('iam')
    existing = iam.list_role_policies(RoleName=IAM__ROLE_NAME).get('PolicyNames', [])
    if IAM__STOP_INSTANCES_POLICY_NAME in existing:
        return {'ok': True, 'action': 'already_exists'}
    iam.put_role_policy(RoleName     = IAM__ROLE_NAME                   ,
                        PolicyName   = IAM__STOP_INSTANCES_POLICY_NAME  ,
                        PolicyDocument = policy_doc                      )
    return {'ok': True, 'action': 'created'}


def ensure_instance_profile() -> str:                                               # Idempotent: ensure role + instance profile + SSM/ECR policy attachments exist
    role = IAM_Role(role_name=IAM__ROLE_NAME)
    if role.not_exists():
        try:
            role.create_for_service__assume_role(IAM__ASSUME_ROLE_SERVICE)
        except Exception as e:
            if 'EntityAlreadyExists' not in str(e):
                raise
    try:                                                                            # Always ensure the instance profile exists and the role is attached — these
        role.create_instance_profile()                                              # calls are idempotent: catch EntityAlreadyExists / LimitExceeded so a partial
    except Exception:                                                               # previous run doesn't leave the profile missing.
        pass
    try:
        role.add_to_instance_profile()
    except Exception:
        pass
    for policy_arn in (*IAM__POLICY_ARNS, *IAM__OBSERVABILITY_POLICY_ARNS):
        role.iam.role_policy_attach(policy_arn)
    ensure_stop_instances_policy()
    return IAM__ROLE_NAME


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

    # ── Security group ──────────────────────────────────────────────────────────

    def ensure_security_group(self) -> str:                                         # Idempotent: ensure the SG exists and the public ingress ports are authorised
        ec2      = self.ec2()
        existing = ec2.security_group(security_group_name=SG__NAME)
        if existing:
            sg_id = existing.get('GroupId')
        else:
            create_result = ec2.security_group_create(security_group_name=SG__NAME, description=SG__DESCRIPTION)
            sg_id         = create_result.get('data', {}).get('security_group_id')
        for port in SG_INGRESS_PORTS:
            try:
                ec2.security_group_authorize_ingress(security_group_id=sg_id, port=port)
            except Exception:
                pass                                                                # rule already exists — idempotent
        return sg_id

    # ── AMI lifecycle ───────────────────────────────────────────────────────────

    def latest_al2023_ami_id(self) -> str:                                          # Resolve the most recent AL2023 base AMI in the current region
        ec2    = self.ec2()
        images = ec2.amis(owner=EC2__AMI_OWNER_AMAZON, name=EC2__AMI_NAME_AL2023, architecture='x86_64')
        images = sorted(images, key=lambda image: image.get('CreationDate', ''), reverse=True)
        if not images:
            raise RuntimeError(f'No AL2023 AMI found matching {EC2__AMI_NAME_AL2023!r} in region {aws_region()!r}')
        return images[0].get('ImageId')

    def create_ami(self, instance_id: str, name: str) -> str:                       # Create an AMI from a stopped/running instance — initial sg:ami-status='untested'
        ec2  = self.ec2()
        resp = ec2.client().create_image(InstanceId       = instance_id,
                                         Name             = name        ,
                                         Description      = f'SG Playwright + agent_mitmproxy - {name}',
                                         NoReboot         = True         ,
                                         TagSpecifications= [{'ResourceType': 'image',
                                                              'Tags': [{'Key': 'Name'              , 'Value': name              },
                                                                       {'Key': TAG__SERVICE_KEY    , 'Value': TAG__SERVICE_VALUE},
                                                                       {'Key': TAG__AMI_STATUS_KEY , 'Value': 'untested'        }]}])
        return resp['ImageId']

    def wait_ami_available(self, ami_id: str, timeout: int = 900) -> bool:          # Poll until 'available' (return True) / 'failed' (return False) / timeout (return False)
        ec2      = self.ec2()
        deadline = time.time() + timeout
        while time.time() < deadline:
            images = ec2.client().describe_images(ImageIds=[ami_id]).get('Images', [])
            state  = images[0]['State'] if images else 'pending'
            if state == 'available':
                return True
            if state == 'failed':
                return False
            time.sleep(15)
        return False

    def tag_ami(self, ami_id: str, status: str) -> None:                            # Set sg:ami-status (untested | healthy | unhealthy) — overwrites the existing value
        self.ec2().client().create_tags(Resources=[ami_id],
                                        Tags     =[{'Key': TAG__AMI_STATUS_KEY, 'Value': status}])

    def latest_healthy_ami(self) -> str:                                            # Most-recently-created sg-playwright AMI tagged sg:ami-status=healthy; None if none exist
        resp   = self.ec2().client().describe_images(
            Filters = [{'Name': f'tag:{TAG__SERVICE_KEY}'   , 'Values': [TAG__SERVICE_VALUE]},
                       {'Name': f'tag:{TAG__AMI_STATUS_KEY}', 'Values': ['healthy']         },
                       {'Name': 'state'                     , 'Values': ['available']       }],
            Owners  = ['self'])
        images = sorted(resp.get('Images', []), key=lambda x: x['CreationDate'], reverse=True)
        return images[0]['ImageId'] if images else None

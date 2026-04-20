# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — provision_mitmproxy_ec2.py (v0.1.32 — EC2 spike)
#
# Spike-grade helper to spin up a single EC2 box running the agent_mitmproxy
# Docker image. Mirrors scripts/provision_ec2.py (the Playwright spike) almost
# line-for-line; the deltas are:
#
#   • Smaller box (t3.small) — mitmproxy + FastAPI admin is not a browser fleet.
#   • Two ingress ports — :8080 (proxy) + :8000 (admin API). mitmweb UI on
#     :8081 stays internal and is proxied via the admin API (Routes__Web).
#   • UserData passes the AGENT_MITMPROXY__PROXY_AUTH_USER / _PASS pair plus
#     the shared FAST_API__AUTH__API_KEY__* env vars the admin middleware
#     expects.
#
# Cleanup: re-run with --terminate. IAM role + SG survive between runs.
#
# Direct boto3 use is the same narrow exception as provision_ec2.py —
# osbot_aws.aws.ec2.EC2.instance_create() does not expose UserData.
#
# Cost note: t3.small on-demand is ~$0.021/h. Always --terminate when done.
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import json
import sys
import textwrap

from osbot_aws.AWS_Config                                                                import AWS_Config
from osbot_aws.aws.ec2.EC2                                                               import EC2
from osbot_aws.aws.iam.IAM_Role                                                          import IAM_Role
from osbot_utils.utils.Env                                                               import get_env

from agent_mitmproxy.docker.Docker__Agent_Mitmproxy__Base                                import IMAGE_NAME


EC2__INSTANCE_TYPE              = 't3.small'                                            # 2 vCPU / 2 GB RAM — mitmproxy + FastAPI fits comfortably; browser fleet sizing is for Playwright, not this
EC2__AMI_NAME_AL2023            = 'al2023-ami-2023.*-x86_64'                            # Same AL2023 pattern as the Playwright spike — latest wins after owner-filter + sort
EC2__AMI_OWNER_AMAZON           = 'amazon'
EC2__PROXY_PORT                 = 8080                                                  # mitmweb --listen-port (HTTP/HTTPS proxy for downstream clients)
EC2__ADMIN_PORT                 = 8000                                                  # FastAPI admin API (/health, /ca/*, /config/*, /ui proxy)

IAM__ROLE_NAME                  = 'agent-mitmproxy-ec2-spike'                           # Instance profile shares the name (osbot_aws convention)
IAM__ECR_READONLY_POLICY_ARN    = 'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly'
IAM__SSM_CORE_POLICY_ARN        = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'  # Lets `aws ssm start-session --target <i-id>` drop into a shell — no SSH, no password, no port 22
IAM__POLICY_ARNS                = (IAM__ECR_READONLY_POLICY_ARN, IAM__SSM_CORE_POLICY_ARN)
IAM__ASSUME_ROLE_SERVICE        = 'ec2.amazonaws.com'

SG__NAME                        = 'agent-mitmproxy-ec2-spike'                           # No 'sg-' prefix — AWS reserves that for SG IDs
SG__DESCRIPTION                 = 'Agent mitmproxy EC2 spike - ingress :8080 proxy + :8000 admin API'  # ASCII-only (AWS GroupDescription rejects non-ASCII)

TAG__NAME                       = 'agent-mitmproxy-ec2-spike'                           # Instance Name tag + discovery filter for --terminate
TAG__STAGE_KEY                  = 'stage'
DEFAULT_STAGE                   = 'dev'

DEFAULT__PROXY_AUTH_USER        = 'agent'                                               # Spike-grade defaults so the script is runnable without a populated .env
DEFAULT__PROXY_AUTH_PASS        = 'spike-pass'
DEFAULT__API_KEY_NAME           = 'X-API-Key'
DEFAULT__API_KEY_VALUE          = 'mitmproxy-spike'

USER_DATA_TEMPLATE = textwrap.dedent("""\
    #!/bin/bash
    set -euxo pipefail

    dnf install -y docker
    systemctl enable --now docker

    TOKEN=$(aws ecr get-login-password --region {region})
    echo "$TOKEN" | docker login --username AWS --password-stdin {registry}

    docker pull {image_uri}

    docker run -d \\
        --restart=always \\
        --name agent-mitmproxy \\
        -p {proxy_port}:{proxy_port} \\
        -p {admin_port}:{admin_port} \\
        -e AGENT_MITMPROXY__PROXY_AUTH_USER='{proxy_auth_user}' \\
        -e AGENT_MITMPROXY__PROXY_AUTH_PASS='{proxy_auth_pass}' \\
        -e FAST_API__AUTH__API_KEY__NAME='{api_key_name}' \\
        -e FAST_API__AUTH__API_KEY__VALUE='{api_key_value}' \\
        {image_uri}
""")


def aws_account_id() -> str:
    return AWS_Config().aws_session_account_id()


def aws_region() -> str:
    return AWS_Config().aws_session_region_name()


def ecr_registry_host() -> str:
    return f'{aws_account_id()}.dkr.ecr.{aws_region()}.amazonaws.com'                   # ECR registry = account + region; image name is appended by default_image_uri()


def default_image_uri() -> str:
    return f'{ecr_registry_host()}/{IMAGE_NAME}:latest'                                 # Mirrors Docker__Agent_Mitmproxy__Base.image_uri()


def ensure_instance_profile() -> str:                                                   # Creates the IAM role + instance profile + managed policies; idempotent
    role = IAM_Role(role_name=IAM__ROLE_NAME)
    if role.not_exists():
        role.create_for_service__assume_role(IAM__ASSUME_ROLE_SERVICE)                  # AssumeRolePolicyDocument: EC2 service principal
        role.create_instance_profile()                                                  # Wrapper around create_instance_profile with InstanceProfileName=role_name
        role.add_to_instance_profile()                                                  # Binds the role to the profile of the same name
    for policy_arn in IAM__POLICY_ARNS:                                                 # attach_role_policy is idempotent — existing roles pick up new managed policies on re-provision without a terminate/recreate
        role.iam.role_policy_attach(policy_arn)
    return IAM__ROLE_NAME                                                               # Returned so run_instances can pass {'Name': ...}


def ensure_security_group(ec2: EC2) -> str:
    existing = ec2.security_group(security_group_name=SG__NAME)
    if existing:
        return existing.get('GroupId')
    create_result     = ec2.security_group_create(security_group_name=SG__NAME, description=SG__DESCRIPTION)
    security_group_id = create_result.get('data', {}).get('security_group_id')
    ec2.security_group_authorize_ingress(security_group_id=security_group_id, port=EC2__PROXY_PORT)  # :8080 from 0.0.0.0/0 — spike only
    ec2.security_group_authorize_ingress(security_group_id=security_group_id, port=EC2__ADMIN_PORT)  # :8000 from 0.0.0.0/0 — spike only; admin is API-key gated at the app layer
    return security_group_id


def latest_al2023_ami_id(ec2: EC2) -> str:
    images = ec2.amis(owner=EC2__AMI_OWNER_AMAZON, name=EC2__AMI_NAME_AL2023, architecture='x86_64')
    images = sorted(images, key=lambda image: image.get('CreationDate', ''), reverse=True)  # Latest CreationDate wins — AMIs are published ~weekly with rolling name suffix
    if not images:
        raise RuntimeError(f'No AL2023 AMI found matching {EC2__AMI_NAME_AL2023!r} in region {aws_region()!r}')
    return images[0].get('ImageId')


def render_user_data(image_uri       : str,
                     proxy_auth_user : str,
                     proxy_auth_pass : str,
                     api_key_name    : str,
                     api_key_value   : str) -> str:
    return USER_DATA_TEMPLATE.format(region          = aws_region()      ,
                                     registry        = ecr_registry_host(),
                                     image_uri       = image_uri         ,
                                     proxy_port      = EC2__PROXY_PORT   ,
                                     admin_port      = EC2__ADMIN_PORT   ,
                                     proxy_auth_user = proxy_auth_user   ,
                                     proxy_auth_pass = proxy_auth_pass   ,
                                     api_key_name    = api_key_name      ,
                                     api_key_value   = api_key_value     )


def run_instance(ec2: EC2, ami_id: str, security_group_id: str, instance_profile_name: str, user_data: str, stage: str) -> str:  # Narrow direct-boto3: osbot_aws.instance_create doesn't pass UserData
    kwargs = {'ImageId'           : ami_id                                                  ,
              'InstanceType'      : EC2__INSTANCE_TYPE                                      ,
              'MinCount'          : 1                                                       ,
              'MaxCount'          : 1                                                       ,
              'IamInstanceProfile': {'Name': instance_profile_name}                         ,
              'SecurityGroupIds'  : [security_group_id]                                     ,
              'UserData'          : user_data                                               ,
              'TagSpecifications' : [{'ResourceType': 'instance',
                                      'Tags'        : [{'Key': 'Name'       , 'Value': TAG__NAME},
                                                       {'Key': TAG__STAGE_KEY, 'Value': stage    }]}]}
    result      = ec2.client().run_instances(**kwargs)
    instance_id = result.get('Instances', [{}])[0].get('InstanceId')
    return instance_id


def find_spike_instance_ids(ec2: EC2) -> list:                                              # All non-terminated instances carrying our Name tag — used by --terminate
    filters   = [{'Name': 'tag:Name'             , 'Values': [TAG__NAME]},
                 {'Name': 'instance-state-name'  , 'Values': ['pending', 'running', 'stopping', 'stopped']}]
    instances = ec2.instances_details(filters=filters)
    return list(instances.keys())


def terminate_spike_instances(ec2: EC2) -> list:
    instance_ids = find_spike_instance_ids(ec2)
    for instance_id in instance_ids:
        ec2.instance_terminate(instance_id)
    return instance_ids


def provision(stage: str = DEFAULT_STAGE, image_uri: str = None, terminate: bool = False) -> dict:
    ec2 = EC2()

    if terminate:
        terminated = terminate_spike_instances(ec2)
        return {'action': 'terminate', 'instance_ids': terminated}

    proxy_auth_user = get_env('AGENT_MITMPROXY__PROXY_AUTH_USER') or DEFAULT__PROXY_AUTH_USER
    proxy_auth_pass = get_env('AGENT_MITMPROXY__PROXY_AUTH_PASS') or DEFAULT__PROXY_AUTH_PASS
    api_key_name    = get_env('FAST_API__AUTH__API_KEY__NAME'   ) or DEFAULT__API_KEY_NAME
    api_key_value   = get_env('FAST_API__AUTH__API_KEY__VALUE'  ) or DEFAULT__API_KEY_VALUE
    image_uri       = image_uri or default_image_uri()

    instance_profile_name = ensure_instance_profile()
    security_group_id     = ensure_security_group(ec2)
    ami_id                = latest_al2023_ami_id(ec2)
    user_data             = render_user_data(image_uri       = image_uri      ,
                                             proxy_auth_user = proxy_auth_user,
                                             proxy_auth_pass = proxy_auth_pass,
                                             api_key_name    = api_key_name   ,
                                             api_key_value   = api_key_value  )

    instance_id = run_instance(ec2                   = ec2                   ,
                               ami_id                = ami_id                ,
                               security_group_id     = security_group_id     ,
                               instance_profile_name = instance_profile_name ,
                               user_data             = user_data             ,
                               stage                 = stage                 )

    ec2.wait_for_instance_running(instance_id)
    details   = ec2.instance_details(instance_id)
    public_ip = details.get('public_ip')
    proxy_url = f'http://{public_ip}:{EC2__PROXY_PORT}' if public_ip else None
    admin_url = f'http://{public_ip}:{EC2__ADMIN_PORT}' if public_ip else None

    return {'action'      : 'create'             ,
            'instance_id' : instance_id          ,
            'public_ip'   : public_ip            ,
            'proxy_url'   : proxy_url            ,
            'admin_url'   : admin_url            ,
            'image_uri'   : image_uri            ,
            'ami_id'      : ami_id               ,
            'stage'       : stage                }


def main() -> int:
    parser = argparse.ArgumentParser(description='Spin up a throwaway EC2 instance running the agent_mitmproxy Docker image (spike — proxy + admin API).')
    parser.add_argument('--stage'    , default=DEFAULT_STAGE, help="Stage tag applied to the instance (default: 'dev')")
    parser.add_argument('--image-uri', default=None         , help='Override ECR image URI (default: <account>.dkr.ecr.<region>.amazonaws.com/agent_mitmproxy:latest)')
    parser.add_argument('--terminate', action='store_true'  , help='Terminate all instances tagged Name=agent-mitmproxy-ec2-spike and exit')
    args = parser.parse_args()

    result = provision(stage=args.stage, image_uri=args.image_uri, terminate=args.terminate)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())

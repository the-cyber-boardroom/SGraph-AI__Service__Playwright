# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — provision_ec2.py (v0.1.33 — two-container EC2 stack)
#
# Provisions an EC2 instance running the full Playwright + agent_mitmproxy
# two-container stack via docker compose. Replaces the separate per-image
# spike scripts (provision_ec2.py v0.1.31 + provision_mitmproxy_ec2.py).
#
# What it does:
#   1. Ensures an IAM role + instance profile with ECR read + SSM access.
#   2. Ensures a security group allowing :8000 (Playwright API) and :8001
#      (sidecar admin API) ingress. The sidecar proxy (:8080) stays on the
#      Docker bridge — never exposed to the host.
#   3. Runs a t3.large AL2023 instance. UserData installs Docker + the Compose
#      plugin, logs into ECR, pulls both images, writes docker-compose.yml and
#      runs `docker compose up -d`.
#   4. Waits for the instance to reach `running`, prints both service URLs.
#
# Cleanup: re-run with --terminate. The SG + IAM role survive between runs
# (idempotent re-create). Delete them manually when the stack is fully torn down.
#
# Direct boto3 use — same narrow exception as earlier versions: osbot_aws
# EC2.instance_create() does not expose the UserData kwarg.
#
# Cost note: t3.large on-demand is ~$0.083/h. Always --terminate when done.
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import json
import sys
import textwrap

from osbot_aws.AWS_Config                                                                import AWS_Config
from osbot_aws.aws.ec2.EC2                                                               import EC2
from osbot_aws.aws.iam.IAM_Role                                                          import IAM_Role
from osbot_utils.utils.Env                                                               import get_env

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base    import IMAGE_NAME as PLAYWRIGHT_IMAGE_NAME
from agent_mitmproxy.docker.Docker__Agent_Mitmproxy__Base                                import IMAGE_NAME as SIDECAR_IMAGE_NAME


EC2__INSTANCE_TYPE           = 't3.large'                                               # 2 vCPU / 8 GB RAM — Playwright + sidecar fit; Firefox + WebKit need the headroom
EC2__AMI_NAME_AL2023         = 'al2023-ami-2023.*-x86_64'
EC2__AMI_OWNER_AMAZON        = 'amazon'
EC2__PLAYWRIGHT_PORT         = 8000                                                     # Playwright API — exposed to the world via SG
EC2__SIDECAR_ADMIN_PORT      = 8001                                                     # Sidecar admin API (host port mapping of container :8000) — exposed via SG, API-key gated

WATCHDOG_MAX_REQUEST_MS      = 120_000                                                  # 120s — covers Firefox + long upstream-proxy round-trips

IAM__ROLE_NAME               = 'sg-playwright-ec2'
IAM__ECR_READONLY_POLICY_ARN = 'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly'
IAM__SSM_CORE_POLICY_ARN     = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'  # SSM session manager — no SSH needed
IAM__POLICY_ARNS             = (IAM__ECR_READONLY_POLICY_ARN, IAM__SSM_CORE_POLICY_ARN)
IAM__ASSUME_ROLE_SERVICE     = 'ec2.amazonaws.com'

SG__NAME                     = 'playwright-ec2'                                         # AWS reserves 'sg-*' prefix for SG IDs
SG__DESCRIPTION              = 'SG Playwright EC2 stack - ingress :8000 (API) + :8001 (sidecar admin)'

TAG__NAME                    = 'sg-playwright-ec2'
TAG__STAGE_KEY               = 'stage'
DEFAULT_STAGE                = 'dev'


COMPOSE_YAML_TEMPLATE = textwrap.dedent("""\
    services:

      playwright:
        image: {playwright_image_uri}
        ports:
          - "{playwright_port}:{playwright_port}"
        environment:
          FAST_API__AUTH__API_KEY__NAME:          '{api_key_name}'
          FAST_API__AUTH__API_KEY__VALUE:         '{api_key_value}'
          SG_PLAYWRIGHT__DEPLOYMENT_TARGET:       container
          SG_PLAYWRIGHT__DEFAULT_PROXY_URL:       http://agent-mitmproxy:8080
          SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS:     'true'
          SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS: {watchdog_max_request_ms}
        networks:
          - sg-net
        depends_on:
          - agent-mitmproxy
        restart: always

      agent-mitmproxy:
        image: {sidecar_image_uri}
        ports:
          - "{sidecar_admin_port}:8000"
        environment:
          FAST_API__AUTH__API_KEY__NAME:  '{api_key_name}'
          FAST_API__AUTH__API_KEY__VALUE: '{api_key_value}'
          AGENT_MITMPROXY__UPSTREAM_URL:  '{upstream_url}'
          AGENT_MITMPROXY__UPSTREAM_USER: '{upstream_user}'
          AGENT_MITMPROXY__UPSTREAM_PASS: '{upstream_pass}'
        networks:
          - sg-net
        restart: always

    networks:
      sg-net:
        driver: bridge
""")


USER_DATA_TEMPLATE = """\
#!/bin/bash
set -euxo pipefail

dnf install -y docker docker-compose-plugin
systemctl enable --now docker

TOKEN=$(aws ecr get-login-password --region {region})
echo "$TOKEN" | docker login --username AWS --password-stdin {registry}

docker pull {playwright_image_uri}
docker pull {sidecar_image_uri}

mkdir -p /opt/sg-playwright

cat > /opt/sg-playwright/docker-compose.yml << 'SG_COMPOSE_EOF'
{compose_content}
SG_COMPOSE_EOF

docker compose -f /opt/sg-playwright/docker-compose.yml up -d
"""


def aws_account_id() -> str:
    return AWS_Config().aws_session_account_id()


def aws_region() -> str:
    return AWS_Config().aws_session_region_name()


def ecr_registry_host() -> str:
    return f'{aws_account_id()}.dkr.ecr.{aws_region()}.amazonaws.com'


def default_playwright_image_uri() -> str:
    return f'{ecr_registry_host()}/{PLAYWRIGHT_IMAGE_NAME}:latest'


def default_sidecar_image_uri() -> str:
    return f'{ecr_registry_host()}/{SIDECAR_IMAGE_NAME}:latest'


def preflight_check(playwright_image_uri: str = None, sidecar_image_uri: str = None) -> dict:
    """Validate AWS credentials + resolve config. Prints a summary and exits on failure."""
    errors = []

    # ── AWS credentials ───────────────────────────────────────────────────────
    _CREDS_HELP = [
        'AWS credentials not found or not valid.',
        '',
        'Provide credentials via one of:',
        '  export AWS_ACCESS_KEY_ID=...    AWS_SECRET_ACCESS_KEY=...    AWS_DEFAULT_REGION=...',
        '  export AWS_PROFILE=<profile>    (uses ~/.aws/credentials)',
        '  aws configure                   (interactive)',
    ]
    try:
        account = aws_account_id()
        region  = aws_region()
    except Exception as exc:
        _print_preflight_error(_CREDS_HELP + ['', f'  Error: {exc}'])

    if not account:                                                                      # AWS_Config returns None (not an exception) when STS call fails
        _print_preflight_error(_CREDS_HELP)

    registry = ecr_registry_host()

    resolved_playwright = playwright_image_uri or f'{registry}/{PLAYWRIGHT_IMAGE_NAME}:latest'
    resolved_sidecar    = sidecar_image_uri    or f'{registry}/{SIDECAR_IMAGE_NAME}:latest'

    # ── API key ───────────────────────────────────────────────────────────────
    api_key_name  = get_env('FAST_API__AUTH__API_KEY__NAME' ) or 'X-API-Key'
    api_key_value = get_env('FAST_API__AUTH__API_KEY__VALUE')
    if not api_key_value:
        errors.append('FAST_API__AUTH__API_KEY__VALUE is not set — containers will use the insecure default "ec2-dev".')
        api_key_value = 'ec2-dev  (default — set FAST_API__AUTH__API_KEY__VALUE to override)'

    # ── Upstream forwarding (optional) ────────────────────────────────────────
    upstream_url  = get_env('AGENT_MITMPROXY__UPSTREAM_URL' ) or ''
    upstream_user = get_env('AGENT_MITMPROXY__UPSTREAM_USER') or ''
    upstream_pass = get_env('AGENT_MITMPROXY__UPSTREAM_PASS') or ''
    if upstream_url and not (upstream_user and upstream_pass):
        errors.append('AGENT_MITMPROXY__UPSTREAM_URL is set but UPSTREAM_USER/PASS are missing — sidecar will try unauthenticated upstream.')

    # ── Print summary ─────────────────────────────────────────────────────────
    lines = [
        '=== provision_ec2.py — preflight ===',
        '',
        'AWS:',
        f'  account  : {account}',
        f'  region   : {region}',
        f'  registry : {registry}',
        '',
        'Images:',
        f'  playwright : {resolved_playwright}',
        f'  sidecar    : {resolved_sidecar}',
        '',
        'API key:',
        f'  name  : {api_key_name}',
        f'  value : {api_key_value}',
        '',
    ]
    if upstream_url:
        lines += [
            'Upstream forwarding:',
            f'  url  : {upstream_url}',
            f'  user : {"(set)" if upstream_user else "(not set)"}',
            f'  pass : {"(set)" if upstream_pass else "(not set)"}',
            '',
        ]
    else:
        lines += ['Upstream forwarding: none (sidecar runs in direct mode)', '']

    lines += [
        f'Stack: t3.large / AL2023 / IAM={IAM__ROLE_NAME} / SG={SG__NAME} / tag={TAG__NAME}',
        f'Ports: playwright :{EC2__PLAYWRIGHT_PORT}  sidecar-admin :{EC2__SIDECAR_ADMIN_PORT}  (proxy :8080 Docker-network-only)',
    ]

    print('\n'.join(lines))

    if errors:
        print('\nWarnings:')
        for e in errors:
            print(f'  ⚠  {e}')

    print()
    return {'account': account, 'region': region, 'registry': registry}


def _print_preflight_error(lines: list) -> None:
    print('\nERROR: ' + '\n       '.join(lines[0:1]))
    for line in lines[1:]:
        print(f'       {line}' if line else '')
    print()
    sys.exit(1)


    role = IAM_Role(role_name=IAM__ROLE_NAME)
    if role.not_exists():
        role.create_for_service__assume_role(IAM__ASSUME_ROLE_SERVICE)
        role.create_instance_profile()
        role.add_to_instance_profile()
    for policy_arn in IAM__POLICY_ARNS:
        role.iam.role_policy_attach(policy_arn)
    return IAM__ROLE_NAME


def ensure_instance_profile() -> str:
    role = IAM_Role(role_name=IAM__ROLE_NAME)
    if role.not_exists():
        role.create_for_service__assume_role(IAM__ASSUME_ROLE_SERVICE)
        role.create_instance_profile()
        role.add_to_instance_profile()
    for policy_arn in IAM__POLICY_ARNS:
        role.iam.role_policy_attach(policy_arn)
    return IAM__ROLE_NAME


def ensure_security_group(ec2: EC2) -> str:
    existing = ec2.security_group(security_group_name=SG__NAME)
    if existing:
        return existing.get('GroupId')
    create_result     = ec2.security_group_create(security_group_name=SG__NAME, description=SG__DESCRIPTION)
    security_group_id = create_result.get('data', {}).get('security_group_id')
    ec2.security_group_authorize_ingress(security_group_id=security_group_id, port=EC2__PLAYWRIGHT_PORT)    # :8000 — Playwright API
    ec2.security_group_authorize_ingress(security_group_id=security_group_id, port=EC2__SIDECAR_ADMIN_PORT) # :8001 — sidecar admin API
    return security_group_id


def latest_al2023_ami_id(ec2: EC2) -> str:
    images = ec2.amis(owner=EC2__AMI_OWNER_AMAZON, name=EC2__AMI_NAME_AL2023, architecture='x86_64')
    images = sorted(images, key=lambda image: image.get('CreationDate', ''), reverse=True)
    if not images:
        raise RuntimeError(f'No AL2023 AMI found matching {EC2__AMI_NAME_AL2023!r} in region {aws_region()!r}')
    return images[0].get('ImageId')


def render_compose_yaml(playwright_image_uri : str,
                         sidecar_image_uri    : str,
                         api_key_name         : str,
                         api_key_value        : str,
                         upstream_url         : str = '',
                         upstream_user        : str = '',
                         upstream_pass        : str = '',
                         watchdog_max_request_ms: int = WATCHDOG_MAX_REQUEST_MS) -> str:
    return COMPOSE_YAML_TEMPLATE.format(playwright_image_uri    = playwright_image_uri    ,
                                        sidecar_image_uri       = sidecar_image_uri       ,
                                        playwright_port         = EC2__PLAYWRIGHT_PORT    ,
                                        sidecar_admin_port      = EC2__SIDECAR_ADMIN_PORT ,
                                        api_key_name            = api_key_name            ,
                                        api_key_value           = api_key_value           ,
                                        upstream_url            = upstream_url            ,
                                        upstream_user           = upstream_user           ,
                                        upstream_pass           = upstream_pass           ,
                                        watchdog_max_request_ms = watchdog_max_request_ms )


def render_user_data(playwright_image_uri : str,
                      sidecar_image_uri    : str,
                      compose_content      : str) -> str:
    return USER_DATA_TEMPLATE.format(region               = aws_region()           ,
                                     registry             = ecr_registry_host()    ,
                                     playwright_image_uri = playwright_image_uri   ,
                                     sidecar_image_uri    = sidecar_image_uri      ,
                                     compose_content      = compose_content        )


def run_instance(ec2: EC2, ami_id: str, security_group_id: str, instance_profile_name: str, user_data: str, stage: str) -> str:
    kwargs = {'ImageId'           : ami_id                                                  ,
              'InstanceType'      : EC2__INSTANCE_TYPE                                      ,
              'MinCount'          : 1                                                       ,
              'MaxCount'          : 1                                                       ,
              'IamInstanceProfile': {'Name': instance_profile_name}                         ,
              'SecurityGroupIds'  : [security_group_id]                                     ,
              'UserData'          : user_data                                               ,
              'TagSpecifications' : [{'ResourceType': 'instance',
                                      'Tags'        : [{'Key': 'Name'        , 'Value': TAG__NAME},
                                                       {'Key': TAG__STAGE_KEY, 'Value': stage    }]}]}
    result      = ec2.client().run_instances(**kwargs)
    instance_id = result.get('Instances', [{}])[0].get('InstanceId')
    return instance_id


def find_instance_ids(ec2: EC2) -> list:
    filters   = [{'Name': 'tag:Name'             , 'Values': [TAG__NAME]},
                 {'Name': 'instance-state-name'  , 'Values': ['pending', 'running', 'stopping', 'stopped']}]
    instances = ec2.instances_details(filters=filters)
    return list(instances.keys())


def terminate_instances(ec2: EC2) -> list:
    instance_ids = find_instance_ids(ec2)
    for instance_id in instance_ids:
        ec2.instance_terminate(instance_id)
    return instance_ids


def provision(stage                  : str  = DEFAULT_STAGE ,
               playwright_image_uri  : str  = None          ,
               sidecar_image_uri     : str  = None          ,
               terminate             : bool = False         ) -> dict:
    ec2 = EC2()

    if terminate:
        terminated = terminate_instances(ec2)
        return {'action': 'terminate', 'instance_ids': terminated}

    api_key_name          = get_env('FAST_API__AUTH__API_KEY__NAME' ) or 'X-API-Key'
    api_key_value         = get_env('FAST_API__AUTH__API_KEY__VALUE') or 'ec2-dev'
    upstream_url          = get_env('AGENT_MITMPROXY__UPSTREAM_URL' ) or ''
    upstream_user         = get_env('AGENT_MITMPROXY__UPSTREAM_USER') or ''
    upstream_pass         = get_env('AGENT_MITMPROXY__UPSTREAM_PASS') or ''
    playwright_image_uri  = playwright_image_uri or default_playwright_image_uri()
    sidecar_image_uri     = sidecar_image_uri    or default_sidecar_image_uri()

    compose_content       = render_compose_yaml(playwright_image_uri = playwright_image_uri ,
                                                 sidecar_image_uri    = sidecar_image_uri    ,
                                                 api_key_name         = api_key_name         ,
                                                 api_key_value        = api_key_value        ,
                                                 upstream_url         = upstream_url         ,
                                                 upstream_user        = upstream_user        ,
                                                 upstream_pass        = upstream_pass        )
    user_data             = render_user_data(playwright_image_uri = playwright_image_uri ,
                                              sidecar_image_uri    = sidecar_image_uri    ,
                                              compose_content      = compose_content      )

    instance_profile_name = ensure_instance_profile()
    security_group_id     = ensure_security_group(ec2)
    ami_id                = latest_al2023_ami_id(ec2)
    instance_id           = run_instance(ec2                   = ec2                   ,
                                          ami_id                = ami_id                ,
                                          security_group_id     = security_group_id     ,
                                          instance_profile_name = instance_profile_name ,
                                          user_data             = user_data             ,
                                          stage                 = stage                 )

    ec2.wait_for_instance_running(instance_id)
    details       = ec2.instance_details(instance_id)
    public_ip     = details.get('public_ip')
    playwright_url = f'http://{public_ip}:{EC2__PLAYWRIGHT_PORT}'    if public_ip else None
    sidecar_url    = f'http://{public_ip}:{EC2__SIDECAR_ADMIN_PORT}' if public_ip else None

    return {'action'              : 'create'               ,
            'instance_id'        : instance_id             ,
            'public_ip'          : public_ip               ,
            'playwright_url'     : playwright_url          ,
            'sidecar_admin_url'  : sidecar_url             ,
            'playwright_image_uri': playwright_image_uri   ,
            'sidecar_image_uri'  : sidecar_image_uri       ,
            'ami_id'             : ami_id                  ,
            'stage'              : stage                   }


def main() -> int:
    parser = argparse.ArgumentParser(description='Provision an EC2 instance running the Playwright + agent_mitmproxy two-container stack via docker compose.')
    parser.add_argument('--stage'                 , default=DEFAULT_STAGE, help="Stage tag applied to the instance (default: 'dev')")
    parser.add_argument('--playwright-image-uri'  , default=None         , help='Override Playwright ECR image URI')
    parser.add_argument('--sidecar-image-uri'     , default=None         , help='Override sidecar ECR image URI')
    parser.add_argument('--terminate'             , action='store_true'  , help='Terminate all instances tagged Name=sg-playwright-ec2 and exit')
    args = parser.parse_args()

    preflight_check(playwright_image_uri = args.playwright_image_uri,
                    sidecar_image_uri    = args.sidecar_image_uri   )

    result = provision(stage                 = args.stage                ,
                        playwright_image_uri  = args.playwright_image_uri ,
                        sidecar_image_uri     = args.sidecar_image_uri    ,
                        terminate             = args.terminate            )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())

# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — provision_ec2.py (v0.1.31 — EC2 spike)
#
# Throwaway spike to reproduce the Lambda Firefox/WebKit hang on a
# full-`/dev/shm` Linux host and confirm all three browser engines work
# when we get off Lambda's Firecracker microVM.
#
# What it does (one shot, intended for local laptop use, not CI):
#   1. Ensures an IAM role + instance profile exist with the AWS-managed
#      AmazonEC2ContainerRegistryReadOnly policy (so the box can `docker pull`
#      the private ECR image).
#   2. Ensures a security group exists allowing port 8000 from 0.0.0.0/0
#      (spike-grade — do NOT leave long-running public URLs up).
#   3. Runs a t3.large AL2023 instance with UserData that installs Docker,
#      logs into ECR, pulls the current image, and runs it on :8000 with
#      the same API-key env var the Lambda has.
#   4. Waits for the instance to reach `running`, prints the public URL,
#      and exits (the container boot + playwright install inside user-data
#      takes a further 30-60s — tail `/var/log/cloud-init-output.log` via
#      EC2 Serial Console if you need to see it).
#
# Cleanup: re-run with --terminate. The SG + IAM role are left behind for
# the next run (idempotent re-create is a no-op). When you're done with the
# spike entirely, delete them by hand — the script does not manage their
# lifecycle.
#
# Direct boto3 use — this module calls `ec2.client().run_instances()`
# directly because osbot_aws.aws.ec2.EC2.instance_create() does not expose
# the UserData kwarg we need. Same narrow-exception pattern as the Lambda
# Function URL `add_permission` call in
# Lambda__Docker__SGraph_AI__Service__Playwright.create_lambda_function_url()
# (both documented under CLAUDE.md §Stack).
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

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base    import IMAGE_NAME


EC2__INSTANCE_TYPE              = 't3.large'                                            # 2 vCPU / 8 GB RAM — enough headroom for Firefox + WebKit which OOM on t3.small
EC2__AMI_NAME_AL2023            = 'al2023-ami-2023.*-x86_64'                            # Canonical AL2023 name pattern (latest wins after owner-filter + sort)
EC2__AMI_OWNER_AMAZON           = 'amazon'
EC2__APP_PORT                   = 8000                                                  # Container listens here; SG opens this to the world for the spike

IAM__ROLE_NAME                  = 'sg-playwright-ec2-spike'                             # Instance profile shares the name (osbot_aws convention)
IAM__ECR_READONLY_POLICY_ARN    = 'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly'
IAM__SSM_CORE_POLICY_ARN        = 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'  # Lets `aws ssm start-session --target <i-id>` drop into a shell — no SSH, no password, no port 22
IAM__POLICY_ARNS                = (IAM__ECR_READONLY_POLICY_ARN, IAM__SSM_CORE_POLICY_ARN)
IAM__ASSUME_ROLE_SERVICE        = 'ec2.amazonaws.com'

SG__NAME                        = 'playwright-ec2-spike'                                # AWS reserves 'sg-*' group names (collides with SG ID format) — drop the 'sg-' prefix
SG__DESCRIPTION                 = 'Playwright service EC2 spike - ingress :8000 to the world'   # AWS GroupDescription rejects non-ASCII (em dash -> hyphen)

TAG__NAME                       = 'sg-playwright-ec2-spike'                             # Instance Name tag + discovery filter for --terminate
TAG__STAGE_KEY                  = 'stage'
DEFAULT_STAGE                   = 'dev'

WATCHDOG_MAX_REQUEST_MS__SPIKE  = 120_000                                               # 120s — Lambda-tuned 28s default kills Firefox + remote-proxy requests mid-flight; EC2 has no external ceiling so a looser cap is fine for spike work

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
        --name sg-playwright \\
        -p {host_port}:{container_port} \\
        -e FAST_API__AUTH__API_KEY__NAME='{api_key_name}' \\
        -e FAST_API__AUTH__API_KEY__VALUE='{api_key_value}' \\
        -e SG_PLAYWRIGHT__DEPLOYMENT_TARGET=container \\
        -e SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS={watchdog_max_request_ms} \\
        {image_uri}
""")


def aws_account_id() -> str:
    return AWS_Config().aws_session_account_id()


def aws_region() -> str:
    return AWS_Config().aws_session_region_name()


def ecr_registry_host() -> str:
    return f'{aws_account_id()}.dkr.ecr.{aws_region()}.amazonaws.com'                   # ECR registry = account + region; image name is appended by default_image_uri()


def default_image_uri() -> str:
    return f'{ecr_registry_host()}/{IMAGE_NAME}:latest'                                 # Mirrors Docker__SGraph_AI__Service__Playwright__Base.image_uri()


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
    create_result = ec2.security_group_create(security_group_name=SG__NAME, description=SG__DESCRIPTION)
    security_group_id = create_result.get('data', {}).get('security_group_id')
    ec2.security_group_authorize_ingress(security_group_id=security_group_id, port=EC2__APP_PORT)  # :8000 from 0.0.0.0/0 — spike only
    return security_group_id


def latest_al2023_ami_id(ec2: EC2) -> str:
    images = ec2.amis(owner=EC2__AMI_OWNER_AMAZON, name=EC2__AMI_NAME_AL2023, architecture='x86_64')
    images = sorted(images, key=lambda image: image.get('CreationDate', ''), reverse=True)  # Latest CreationDate wins — AMIs are published ~weekly with rolling name suffix
    if not images:
        raise RuntimeError(f'No AL2023 AMI found matching {EC2__AMI_NAME_AL2023!r} in region {aws_region()!r}')
    return images[0].get('ImageId')


def render_user_data(image_uri: str, api_key_name: str, api_key_value: str, watchdog_max_request_ms: int = WATCHDOG_MAX_REQUEST_MS__SPIKE) -> str:
    return USER_DATA_TEMPLATE.format(region                  = aws_region()             ,
                                     registry                = ecr_registry_host()      ,
                                     image_uri               = image_uri                ,
                                     host_port               = EC2__APP_PORT            ,
                                     container_port          = EC2__APP_PORT            ,
                                     api_key_name            = api_key_name             ,
                                     api_key_value           = api_key_value            ,
                                     watchdog_max_request_ms = watchdog_max_request_ms  )


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
    result     = ec2.client().run_instances(**kwargs)
    instance_id = result.get('Instances', [{}])[0].get('InstanceId')
    return instance_id


def find_spike_instance_ids(ec2: EC2) -> list:                                              # All non-terminated instances carrying our Name tag — used by --terminate
    filters   = [{'Name': 'tag:Name'         , 'Values': [TAG__NAME]},
                 {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}]
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

    api_key_name  = get_env('FAST_API__AUTH__API_KEY__NAME' ) or 'X-API-Key'                # Defaults keep the spike runnable without a populated .env
    api_key_value = get_env('FAST_API__AUTH__API_KEY__VALUE') or 'ec2-spike'
    image_uri     = image_uri or default_image_uri()

    instance_profile_name = ensure_instance_profile()
    security_group_id     = ensure_security_group(ec2)
    ami_id                = latest_al2023_ami_id(ec2)
    user_data             = render_user_data(image_uri=image_uri, api_key_name=api_key_name, api_key_value=api_key_value)

    instance_id = run_instance(ec2                   = ec2                   ,
                               ami_id                = ami_id                ,
                               security_group_id     = security_group_id     ,
                               instance_profile_name = instance_profile_name ,
                               user_data             = user_data             ,
                               stage                 = stage                 )

    ec2.wait_for_instance_running(instance_id)
    details   = ec2.instance_details(instance_id)
    public_ip = details.get('public_ip')
    base_url  = f'http://{public_ip}:{EC2__APP_PORT}' if public_ip else None

    return {'action'      : 'create'             ,
            'instance_id' : instance_id          ,
            'public_ip'   : public_ip            ,
            'base_url'    : base_url             ,
            'image_uri'   : image_uri            ,
            'ami_id'      : ami_id               ,
            'stage'       : stage                }


def main() -> int:
    parser = argparse.ArgumentParser(description='Spin up a throwaway EC2 instance running the Playwright Docker image (spike — Firefox/WebKit off Lambda).')
    parser.add_argument('--stage'    , default=DEFAULT_STAGE, help="Stage tag applied to the instance (default: 'dev')")
    parser.add_argument('--image-uri', default=None         , help='Override ECR image URI (default: <account>.dkr.ecr.<region>.amazonaws.com/sgraph_ai_service_playwright:latest)')
    parser.add_argument('--terminate', action='store_true'  , help='Terminate all instances tagged Name=sg-playwright-ec2-spike and exit')
    args = parser.parse_args()

    result = provision(stage=args.stage, image_uri=args.image_uri, terminate=args.terminate)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())

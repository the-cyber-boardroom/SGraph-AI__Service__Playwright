# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__EC2
# Pre-flight check for the *shared* EC2 prerequisites that every vault-app
# launch depends on. Each register creates a fresh stack from scratch, so
# there is no default/template instance to verify — only:
#
#   1. The IAM instance profile `playwright-ec2` exists (SSM + ECR access).
#   2. The Amazon Linux 2023 base AMI is resolvable via the standard SSM
#      public parameter in the target region.
#
# Check-only. There is no create()/delete() — the IAM profile is created
# out-of-band by the platform team, and the AMI parameter is AWS-managed.
# A missing profile is flagged as a blocker; a missing AMI parameter is
# almost certainly a wrong region.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Callable, Optional

import boto3                                                                          # EXCEPTION — single boto3 boundary for two read calls
from botocore.exceptions import ClientError

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Issue           import Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__EC2__Report     import Schema__Setup__EC2__Report

PROFILE_NAME     = 'playwright-ec2'
AL2023_SSM_PARAM = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'


class Setup__EC2(Type_Safe):
    _iam_client_factory : Optional[Callable] = None
    _ssm_client_factory : Optional[Callable] = None
    region              : str = ''

    def _iam(self):
        if self._iam_client_factory:
            return self._iam_client_factory()
        return boto3.client('iam')                                                     # IAM is global

    def _ssm(self):
        if self._ssm_client_factory:
            return self._ssm_client_factory()
        region = self.region or self._resolved_region()
        return boto3.client('ssm', region_name=region)

    def _resolved_region(self) -> str:
        from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver import Aws__Region__Resolver
        return str(Aws__Region__Resolver().resolve())

    # ── read ─────────────────────────────────────────────────────────────────

    def check(self) -> Schema__Setup__EC2__Report:
        issues = List__Schema__Setup__Issue()
        region = self.region or self._resolved_region()

        profile_exists, profile_arn = self._check_profile()
        if not profile_exists:
            issues.append(Schema__Setup__Issue(
                severity='error', area='ec2',
                message=f'IAM instance profile {PROFILE_NAME!r} not found — '
                        'required for vault-app EC2 (SSM + ECR access)'))

        ami_id, ami_resolvable = self._check_ami(region)
        if not ami_resolvable:
            issues.append(Schema__Setup__Issue(
                severity='error', area='ec2',
                message=f'AL2023 AMI parameter not resolvable in {region} — '
                        f'check region or that {AL2023_SSM_PARAM!r} exists'))

        state = (Enum__Setup__State.OK if (profile_exists and ami_resolvable)
                 else Enum__Setup__State.MISSING)
        return Schema__Setup__EC2__Report(
            state          = state,
            region         = region,
            profile_name   = PROFILE_NAME,
            profile_exists = profile_exists,
            profile_arn    = profile_arn,
            ami_id         = ami_id,
            ami_resolvable = ami_resolvable,
            issues         = issues,
        )

    def status(self) -> dict:
        region = self.region or self._resolved_region()
        _, profile_arn = self._check_profile()
        ami_id, _      = self._check_ami(region)
        return {
            'region'         : region,
            'profile_name'   : PROFILE_NAME,
            'profile_arn'    : profile_arn or '(not found)',
            'ami_param'      : AL2023_SSM_PARAM,
            'ami_id'         : ami_id or '(not resolvable)',
        }

    # ── internal ─────────────────────────────────────────────────────────────

    def _check_profile(self):
        try:
            resp    = self._iam().get_instance_profile(InstanceProfileName=PROFILE_NAME)
            profile = resp.get('InstanceProfile', {})
            return True, profile.get('Arn', '')
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code in ('NoSuchEntity', 'NoSuchEntityException'):
                return False, ''
            raise

    def _check_ami(self, region: str):
        try:
            resp  = self._ssm().get_parameter(Name=AL2023_SSM_PARAM)
            value = resp.get('Parameter', {}).get('Value', '')
            return value, bool(value)
        except ClientError:
            return '', False

# ═══════════════════════════════════════════════════════════════════════════════
# Tests — scripts/provision_ec2.py (v0.1.31 — EC2 spike)
#
# Scope (unit-level, no real AWS):
#   • module surface            — exposes provision / main / the pure helpers.
#   • constants                 — t3.large, AL2023 AMI pattern, :8000, SG name.
#   • user-data rendering       — includes image URI, ECR login, run command,
#                                  API-key env vars.
#   • provision(--terminate)    — short-circuits (no real AWS work needed when
#                                  the EC2 facade is stubbed out).
#
# End-to-end create/terminate verification is out of scope — the script is a
# local-only spike, not a deployed surface.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                            import TestCase

from scripts                                                                             import provision_ec2
from scripts.provision_ec2                                                               import (DEFAULT_STAGE                ,
                                                                                                 EC2__AMI_NAME_AL2023          ,
                                                                                                 EC2__APP_PORT                 ,
                                                                                                 EC2__INSTANCE_TYPE            ,
                                                                                                 IAM__ECR_READONLY_POLICY_ARN  ,
                                                                                                 IAM__POLICY_ARNS              ,
                                                                                                 IAM__ROLE_NAME                ,
                                                                                                 IAM__SSM_CORE_POLICY_ARN      ,
                                                                                                 SG__NAME                      ,
                                                                                                 TAG__NAME                     ,
                                                                                                 render_user_data              )


class test_module_surface(TestCase):

    def test__exposes_expected_symbols(self):
        for attr in ('provision'                   ,
                     'main'                        ,
                     'render_user_data'            ,
                     'default_image_uri'           ,
                     'ensure_instance_profile'     ,
                     'ensure_security_group'       ,
                     'latest_al2023_ami_id'        ,
                     'run_instance'                ,
                     'find_spike_instance_ids'     ,
                     'terminate_spike_instances'   ):
            assert hasattr(provision_ec2, attr), f'missing: {attr}'


class test_constants(TestCase):

    def test__spike_pins_match_design(self):                                              # Pinned values are contract with the operator — changing them is a breaking change for in-flight spike sessions
        assert EC2__INSTANCE_TYPE           == 't3.large'
        assert EC2__APP_PORT                == 8000
        assert EC2__AMI_NAME_AL2023         .startswith('al2023-ami-')
        assert IAM__ECR_READONLY_POLICY_ARN == 'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly'
        assert IAM__SSM_CORE_POLICY_ARN     == 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
        assert IAM__POLICY_ARNS             == (IAM__ECR_READONLY_POLICY_ARN, IAM__SSM_CORE_POLICY_ARN)
        assert IAM__ROLE_NAME               == 'sg-playwright-ec2-spike'
        assert SG__NAME                     == 'playwright-ec2-spike'                     # AWS rejects group names matching 'sg-*' (reserved for SG IDs)
        assert TAG__NAME                    == 'sg-playwright-ec2-spike'
        assert DEFAULT_STAGE                == 'dev'


class test_render_user_data(TestCase):

    def test__includes_docker_install_and_ecr_pull_and_run(self):
        image_uri = '123456789012.dkr.ecr.eu-west-1.amazonaws.com/sgraph_ai_service_playwright:latest'
        original  = provision_ec2.aws_region
        try:
            provision_ec2.aws_region = lambda: 'eu-west-1'                                # Bypass AWS_Config read — render_user_data inlines region + registry host
            user_data = render_user_data(image_uri=image_uri, api_key_name='X-API-Key', api_key_value='spike-secret')
        finally:
            provision_ec2.aws_region = original

        assert user_data.startswith('#!/bin/bash')
        assert 'dnf install -y docker'                                                 in user_data
        assert 'aws ecr get-login-password --region eu-west-1'                          in user_data
        assert 'docker login --username AWS --password-stdin'                           in user_data
        assert f'docker pull {image_uri}'                                               in user_data
        assert f'-p {EC2__APP_PORT}:{EC2__APP_PORT}'                                    in user_data
        assert "-e FAST_API__AUTH__API_KEY__NAME='X-API-Key'"                           in user_data
        assert "-e FAST_API__AUTH__API_KEY__VALUE='spike-secret'"                       in user_data
        assert '-e SG_PLAYWRIGHT__DEPLOYMENT_TARGET=container'                          in user_data
        assert '-e SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS=120000'                       in user_data     # Lambda-tuned 28s default kills Firefox + proxy mid-flight; 120s is safe for the spike
        assert '--restart=always'                                                       in user_data


class test_provision_terminate(TestCase):                                                 # --terminate short-circuits before any create path runs

    def test__terminate_calls_terminate_helper_only(self):
        terminate_calls = []

        original = provision_ec2.terminate_spike_instances
        try:
            provision_ec2.terminate_spike_instances = lambda ec2: terminate_calls.append(ec2) or ['i-stub']
            result = provision_ec2.provision(terminate=True)
        finally:
            provision_ec2.terminate_spike_instances = original

        assert len(terminate_calls) == 1                                                  # Facade passed through unchanged
        assert result               == {'action': 'terminate', 'instance_ids': ['i-stub']}


class test_argparse(TestCase):

    def test__terminate_is_off_by_default(self):                                          # Safety: invoking with no args must not wipe any running spike instance
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--stage'    , default=DEFAULT_STAGE)
        parser.add_argument('--image-uri', default=None)
        parser.add_argument('--terminate', action='store_true')
        args = parser.parse_args([])
        assert args.terminate is False
        assert args.stage     == DEFAULT_STAGE
        assert args.image_uri is None

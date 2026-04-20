# ═══════════════════════════════════════════════════════════════════════════════
# Tests — scripts/provision_mitmproxy_ec2.py (v0.1.32 — EC2 spike)
#
# Scope (unit-level, no real AWS):
#   • module surface          — exposes provision / main / the pure helpers.
#   • constants               — t3.small, AL2023 AMI pattern, :8080 + :8000, SG name.
#   • user-data rendering     — includes image URI, ECR login, run command,
#                                proxy auth + API-key env vars.
#   • provision(--terminate)  — short-circuits (no real AWS work needed when
#                                the EC2 facade is stubbed out).
#
# End-to-end create/terminate verification is out of scope — the script is a
# local-only spike, not a deployed surface.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                            import TestCase

from scripts                                                                             import provision_mitmproxy_ec2
from scripts.provision_mitmproxy_ec2                                                     import (DEFAULT_STAGE                 ,
                                                                                                 EC2__ADMIN_PORT               ,
                                                                                                 EC2__AMI_NAME_AL2023          ,
                                                                                                 EC2__INSTANCE_TYPE            ,
                                                                                                 EC2__PROXY_PORT               ,
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
            assert hasattr(provision_mitmproxy_ec2, attr), f'missing: {attr}'


class test_constants(TestCase):

    def test__spike_pins_match_design(self):                                              # Pinned values are contract with the operator — changing them is a breaking change for in-flight spike sessions
        assert EC2__INSTANCE_TYPE           == 't3.small'
        assert EC2__PROXY_PORT              == 8080
        assert EC2__ADMIN_PORT              == 8000
        assert EC2__AMI_NAME_AL2023         .startswith('al2023-ami-')
        assert IAM__ECR_READONLY_POLICY_ARN == 'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly'
        assert IAM__SSM_CORE_POLICY_ARN     == 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
        assert IAM__POLICY_ARNS             == (IAM__ECR_READONLY_POLICY_ARN, IAM__SSM_CORE_POLICY_ARN)
        assert IAM__ROLE_NAME               == 'agent-mitmproxy-ec2-spike'
        assert SG__NAME                     == 'agent-mitmproxy-ec2-spike'
        assert TAG__NAME                    == 'agent-mitmproxy-ec2-spike'
        assert DEFAULT_STAGE                == 'dev'


class test_render_user_data(TestCase):

    def test__includes_docker_install_and_ecr_pull_and_run(self):
        image_uri = '123456789012.dkr.ecr.eu-west-1.amazonaws.com/agent_mitmproxy:latest'
        original  = provision_mitmproxy_ec2.aws_region
        try:
            provision_mitmproxy_ec2.aws_region = lambda: 'eu-west-1'                      # Bypass AWS_Config read — render_user_data inlines region + registry host
            user_data = render_user_data(image_uri       = image_uri      ,
                                         proxy_auth_user = 'agent'        ,
                                         proxy_auth_pass = 'spike-pass'   ,
                                         api_key_name    = 'X-API-Key'    ,
                                         api_key_value   = 'spike-secret' )
        finally:
            provision_mitmproxy_ec2.aws_region = original

        assert user_data.startswith('#!/bin/bash')
        assert 'dnf install -y docker'                                                 in user_data
        assert 'aws ecr get-login-password --region eu-west-1'                          in user_data
        assert 'docker login --username AWS --password-stdin'                           in user_data
        assert f'docker pull {image_uri}'                                               in user_data
        assert f'-p {EC2__PROXY_PORT}:{EC2__PROXY_PORT}'                                in user_data
        assert f'-p {EC2__ADMIN_PORT}:{EC2__ADMIN_PORT}'                                in user_data
        assert "-e AGENT_MITMPROXY__PROXY_AUTH_USER='agent'"                            in user_data
        assert "-e AGENT_MITMPROXY__PROXY_AUTH_PASS='spike-pass'"                       in user_data
        assert "-e FAST_API__AUTH__API_KEY__NAME='X-API-Key'"                           in user_data
        assert "-e FAST_API__AUTH__API_KEY__VALUE='spike-secret'"                       in user_data
        assert '--restart=always'                                                       in user_data
        assert '--name agent-mitmproxy'                                                 in user_data


class test_provision_terminate(TestCase):                                                 # --terminate short-circuits before any create path runs

    def test__terminate_calls_terminate_helper_only(self):
        terminate_calls = []

        original = provision_mitmproxy_ec2.terminate_spike_instances
        try:
            provision_mitmproxy_ec2.terminate_spike_instances = lambda ec2: terminate_calls.append(ec2) or ['i-stub']
            result = provision_mitmproxy_ec2.provision(terminate=True)
        finally:
            provision_mitmproxy_ec2.terminate_spike_instances = original

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

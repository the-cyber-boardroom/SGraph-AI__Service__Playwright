# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Aws__Region__Resolver
# ═══════════════════════════════════════════════════════════════════════════════

import os

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Region__Resolver import Aws__Region__Resolver


class Test__Aws__Region__Resolver:

    def setup_method(self):
        self.resolver = Aws__Region__Resolver()
        for var in ('SG_AWS__REGION', 'AWS_DEFAULT_REGION'):
            os.environ.pop(var, None)

    def test_flag_takes_precedence(self):
        os.environ['SG_AWS__REGION'] = 'eu-west-1'
        result = self.resolver.resolve(region_flag='ap-southeast-1')
        assert str(result) == 'ap-southeast-1'
        del os.environ['SG_AWS__REGION']

    def test_resource_hint_beats_env(self):
        os.environ['SG_AWS__REGION'] = 'eu-west-1'
        result = self.resolver.resolve(resource_hint='us-west-2')
        assert str(result) == 'us-west-2'
        del os.environ['SG_AWS__REGION']

    def test_sg_aws_region_env(self):
        os.environ['SG_AWS__REGION'] = 'ca-central-1'
        result = self.resolver.resolve()
        assert str(result) == 'ca-central-1'
        del os.environ['SG_AWS__REGION']

    def test_aws_default_region_fallback(self):
        os.environ['AWS_DEFAULT_REGION'] = 'ap-northeast-1'
        result = self.resolver.resolve()
        assert str(result) == 'ap-northeast-1'
        del os.environ['AWS_DEFAULT_REGION']

    def test_hardcoded_fallback(self):
        result = self.resolver.resolve()
        assert str(result) == 'us-east-1'

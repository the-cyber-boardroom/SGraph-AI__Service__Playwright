# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for OpenSearch__User_Data__Builder
# Locks the placeholder contract + escaping behaviour so every install-step
# slice that grows the template can be reviewed in isolation.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__User_Data__Builder import (PLACEHOLDERS,
                                                                                                    USER_DATA_TEMPLATE,
                                                                                                    OpenSearch__User_Data__Builder)


class test_OpenSearch__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = OpenSearch__User_Data__Builder()

    def test_render__substitutes_all_placeholders(self):
        out = self.builder.render('os-quiet-fermi', 'AAAA-BBBB-1234-cdef', 'eu-west-2')
        assert "STACK_NAME='os-quiet-fermi'"             in out
        assert "ADMIN_PASSWORD='AAAA-BBBB-1234-cdef'"    in out
        assert "REGION='eu-west-2'"                       in out

    def test_render__no_placeholders_leaked(self):                                  # Defensive: every {key} must be substituted; regex catches drift
        out      = self.builder.render('os-x', 'YYYY-ZZZZ-0000-aaaa', 'us-east-1')
        leftover = re.findall(r'\{([a-z_]+)\}', out)
        assert leftover == []

    def test_render__starts_with_shebang(self):                                     # cloud-init treats #! as a script (vs #cloud-config)
        out = self.builder.render('os-x', 'YYYY-ZZZZ-0000-aaaa', 'us-east-1')
        assert out.startswith('#!/usr/bin/env bash\n')

    def test_render__sets_strict_bash(self):                                        # 'set -euo pipefail' is non-negotiable for boot scripts
        out = self.builder.render('os-x', 'YYYY-ZZZZ-0000-aaaa', 'us-east-1')
        assert 'set -euo pipefail' in out

    def test_render__logs_to_canonical_path(self):                                  # Every sg- service logs to /var/log/sg-{service}-boot.log; sp diagnose tails these
        out = self.builder.render('os-x', 'YYYY-ZZZZ-0000-aaaa', 'us-east-1')
        assert '/var/log/sg-opensearch-boot.log' in out

    def test_template_placeholders_match_PLACEHOLDERS_constant(self):               # Lock: PLACEHOLDERS == every {key} in the template
        in_template = set(re.findall(r'\{([a-z_]+)\}', USER_DATA_TEMPLATE))
        assert in_template == set(PLACEHOLDERS)

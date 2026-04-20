# ═══════════════════════════════════════════════════════════════════════════════
# Tests — scripts/provision_mitmproxy_ec2.py (PROPOSED — not yet implemented)
#
# scripts/provision_mitmproxy_ec2.py is a planned standalone EC2 provisioner
# for a mitmproxy-only stack (no Playwright sidecar). It has NOT been created
# yet. The combined two-container stack (playwright + agent-mitmproxy) is
# provisioned by scripts/provision_ec2.py.
#
# This file exists to satisfy the reference in .github/workflows/ci__agent_mitmproxy.yml.
# Replace with real tests when provision_mitmproxy_ec2.py is implemented.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest


@pytest.mark.skip(reason='scripts/provision_mitmproxy_ec2.py is PROPOSED — not yet implemented')
def test__provision_mitmproxy_ec2_placeholder():
    pass

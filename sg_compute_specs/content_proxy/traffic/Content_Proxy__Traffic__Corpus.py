# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: traffic corpus registry
# The labelled fixture set the QA path replays through the workflow. A registry
# (logic) — the one allowed module-of-functions exception. Fixture HTML lives in
# corpus/*.html next to this file.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Flow__Action          import Enum__Content_Proxy__Flow__Action
from sg_compute_specs.content_proxy.traffic.Schema__Content_Proxy__Traffic__Case      import Schema__Content_Proxy__Traffic__Case


def default_cases():
    A = Enum__Content_Proxy__Flow__Action
    return [
        Schema__Content_Proxy__Traffic__Case(name='pii_table',      label='should-blur',   url='corpus/pii_table.html',     expected=A.INJECTED),
        Schema__Content_Proxy__Traffic__Case(name='tracking_pixel', label='should-remove', url='corpus/tracking_pixel.html', expected=A.INJECTED),
        Schema__Content_Proxy__Traffic__Case(name='plain_article',  label='should-pass',   url='corpus/plain_article.html',  expected=A.PASSED),
        Schema__Content_Proxy__Traffic__Case(name='static_bundle',  label='should-skip',   url='corpus/static_bundle.js',    expected=A.SKIPPED),
    ]

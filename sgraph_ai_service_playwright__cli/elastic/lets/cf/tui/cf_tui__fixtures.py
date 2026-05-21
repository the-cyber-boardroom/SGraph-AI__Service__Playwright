# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: cf_tui__fixtures
# Real CloudFront real-time TSV lines used by the in-memory source's default demo
# and by tests. VERBATIM from the user's pasted production log lines (the same
# golden samples pinned in test_CF__Realtime__Log__Parser). Not fabricated traffic —
# the in-memory source labels itself "fixtures" so the screen never implies it is
# live. `--source s3` reads the live bucket instead.
# ═══════════════════════════════════════════════════════════════════════════════

# wpbot → /enhancecp, 302 from a CloudFront Function (FunctionGeneratedResponse)
LINE_ENHANCECP = '1777075217.167\t0.001\t302\t246\tGET\thttps\tsgraph.ai\t/enhancecp\tHIO52-P4\t2TZI-f7L0PmDR-76lAEx4wdq-StamTTbisIdbMSYhB4eVeyTcPy0qw==\t0.001\tHTTP/2.0\tMozilla/5.0%20(compatible;%20wpbot/1.4;%20+https://forms.gle/ajBaxygz9jSR8p8G9)\t-\tFunctionGeneratedResponse\tTLSv1.3\tTLS_AES_128_GCM_SHA256\t-\t0\t-\t-\tUS\tgzip\t-\t-\t-'

# wpbot → /robots.txt, 403 (Error result type) with an origin call
LINE_ROBOTS    = '1777075217.160\t0.924\t403\t363\tGET\thttps\tsgraph.ai\t/robots.txt\tHIO52-P4\tBMtxwcXadQXVuawbKov5bSBaxNrAxnxuEI-8RU1AH4i5hUSarxBZwA==\t0.924\tHTTP/2.0\tMozilla/5.0%20(compatible;%20wpbot/1.4;%20+https://forms.gle/ajBaxygz9jSR8p8G9)\t-\tError\tTLSv1.3\tTLS_AES_128_GCM_SHA256\tapplication/xml\t-\t-\t-\tUS\tgzip\t-\t0.424\t0.424'

FIXTURE_TSV = '\n'.join([LINE_ENHANCECP, LINE_ROBOTS])

# The golden lines carry an embedded delivery time of 2026-04-21 08:00; present them
# as two real files under that real partition so the folder browser is navigable with
# no AWS (cloudfront-realtime/YYYY/MM/DD/HH/...). Not fabricated traffic — the same
# real lines, placed under the path they actually belong to.
FIXTURE_FILE_KEYS = ('cloudfront-realtime/2026/04/21/08/sgsend-cf-1-2026-04-21-08-00-17-a1b2c3d4.gz',
                     'cloudfront-realtime/2026/04/21/08/sgsend-cf-1-2026-04-21-08-00-18-e5f6a7b8.gz')


def fixture_files():                                                                 # → List__CF_TUI__Fixture_File of the two golden lines under their real partition
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.List__CF_TUI__Fixture_File  import List__CF_TUI__Fixture_File
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Fixture_File import Schema__CF_TUI__Fixture_File
    files = List__CF_TUI__Fixture_File()
    files.append(Schema__CF_TUI__Fixture_File(key=FIXTURE_FILE_KEYS[0], tsv_text=LINE_ENHANCECP))
    files.append(Schema__CF_TUI__Fixture_File(key=FIXTURE_FILE_KEYS[1], tsv_text=LINE_ROBOTS))
    return files

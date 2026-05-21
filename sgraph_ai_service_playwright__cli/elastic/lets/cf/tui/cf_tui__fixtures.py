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

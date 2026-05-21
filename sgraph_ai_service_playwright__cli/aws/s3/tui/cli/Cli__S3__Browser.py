# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — s3 tui: Cli__S3__Browser
# Backs `sg aws s3 browse [s3://bucket/prefix]` — the interactive S3 browser. Textual
# is imported lazily inside run_browse so importing this module never requires it.
# When stdout is not a TTY (piped / CI) it prints a static listing and returns — safe
# to pipe. The source is built via a factory seam tests can replace (no AWS, no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

import sys

_source_factory = None                                                               # tests assign a callable() → S3_Browser__Source


def source():
    if _source_factory is not None:
        return _source_factory()
    from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client       import S3__AWS__Client
    from sgraph_ai_service_playwright__cli.aws.s3.service.S3__Format__Detector  import S3__Format__Detector
    from sgraph_ai_service_playwright__cli.aws.s3.tui.source.S3_Browser__Source import S3_Browser__Source
    return S3_Browser__Source(client=S3__AWS__Client(), detector=S3__Format__Detector())


def parse_s3_uri(path : str) -> tuple:                                               # 's3://bucket/a/b' → ('bucket', 'a/b'); '' → ('', '')
    p = path[5:] if path.startswith('s3://') else path
    if not p:
        return '', ''
    parts = p.split('/', 1)
    return parts[0], (parts[1] if len(parts) > 1 else '')


def run_browse(path : str = '') -> None:
    src            = source()
    bucket, prefix = parse_s3_uri(path)
    if not sys.stdout.isatty():                                                      # piped / CI → static listing
        from sgraph_ai_service_playwright__cli.aws.s3.tui.screens.S3_Browser__Render import entries_plain
        if bucket:
            print(entries_plain(list(src.list_dir(bucket, prefix)), f's3://{bucket}/{prefix}'))
        else:
            print(entries_plain(list(src.list_buckets()), 's3://'))
        return
    from sgraph_ai_service_playwright__cli.aws.s3.tui.screens.S3_Browser__Screen import S3_Browser__Screen
    S3_Browser__Screen(source=src, start_bucket=bucket, start_prefix=prefix).run()

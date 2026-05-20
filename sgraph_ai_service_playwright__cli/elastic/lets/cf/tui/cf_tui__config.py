# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: cf_tui__config
# Shared constants for the CloudFront-logs TUI (data layer + screens). Mirrors the
# sg_edge tui config: refresh is deliberately slow (every redraw is bytes over the
# SSH/SSM chain), defaults pick the no-AWS in-memory source so the screens run
# anywhere, and the real CF-logs bucket/prefix are the defaults for `--source s3`.
# No fabricated data — the in-memory source parses real CF log lines.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.enums.Enum__CF_TUI__Source import Enum__CF_TUI__Source

TUI_REFRESH_SECONDS = 2.0                                                            # poll cadence; calmer than 60 FPS, kinder to flaky links
TUI_DEFAULT_SOURCE  = Enum__CF_TUI__Source.IN_MEMORY                                  # runs with no AWS; `--source s3` reads the live bucket
TUI_DEFAULT_THEME   = 'dark'
TUI_CARD_WIDTH      = 64                                                              # ASCII export card inner width
TUI_TOP_N           = 6                                                              # rows shown in top-URI / top-bot / country panels

# The live CloudFront real-time-logs bucket Firehose writes to (reality doc: lets/).
CF_LOGS_BUCKET      = '745506449035--sgraph-send-cf-logs--eu-west-2'
CF_LOGS_PREFIX      = 'cloudfront-realtime/'                                          # date-partitioned under here: {YYYY}/{MM}/{DD}/{HH}/
CF_LOGS_REGION      = 'eu-west-2'
TUI_S3_SAMPLE_FILES = 25                                                             # newest .gz objects sampled per refresh for the "live" view

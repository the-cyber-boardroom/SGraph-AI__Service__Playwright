# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — CF__Inventory__Dashboard__Ids
# Single source of truth for the CloudFront-inventory dashboard saved-object
# ids.  Imported by both:
#   - Inventory__Wiper (slice 1, Phase 4) — to delete the dashboard's saved
#     objects on `wipe` even before the dashboard exists, so wipe is
#     forward-compatible with Phase 5.
#   - CF__Inventory__Dashboard__Builder (slice 1, Phase 5) — to assign the
#     same deterministic ids when building the saved-objects ndjson, so
#     re-imports overwrite cleanly.
#
# Mirrors the (id constants + helper function) pattern used by
# Default__Dashboard__Generator for the synthetic-data dashboard.
#
# Slug naming: "sg-cf-inv-vis-{slug}" — matches the brief
# (04__elastic-and-dashboard.md, "Visualisations" row).
# ═══════════════════════════════════════════════════════════════════════════════


DASHBOARD_ID    = 'sg-cf-inventory-overview'                                        # Saved-object id of the dashboard itself
DASHBOARD_TITLE = 'CloudFront Logs - Inventory Overview'                            # User-visible title

VIS_ID__COUNT_OVER_TIME           = 'sg-cf-inv-vis-count-over-time'                 # Panel 1 — line chart, count() over date_histogram(delivery_at)
VIS_ID__BYTES_OVER_TIME           = 'sg-cf-inv-vis-bytes-over-time'                 # Panel 2 — stacked bar, sum(size_bytes) split by delivery_day
VIS_ID__SIZE_DISTRIBUTION         = 'sg-cf-inv-vis-size-distribution'               # Panel 3 — histogram on size_bytes
VIS_ID__STORAGE_CLASS_BREAKDOWN   = 'sg-cf-inv-vis-storage-class-breakdown'         # Panel 4 — donut, terms(storage_class)
VIS_ID__TOP_HOURLY_PARTITIONS     = 'sg-cf-inv-vis-top-hourly-partitions'           # Panel 5 — horizontal bar, terms(delivery_year/month/day/hour)


def all_inventory_dashboard_refs() -> list:                                         # The (type, id) tuples Inventory__Wiper passes to delete_saved_objects()
    return [('dashboard'    , DASHBOARD_ID                     ),
            ('visualization', VIS_ID__COUNT_OVER_TIME            ),
            ('visualization', VIS_ID__BYTES_OVER_TIME            ),
            ('visualization', VIS_ID__SIZE_DISTRIBUTION          ),
            ('visualization', VIS_ID__STORAGE_CLASS_BREAKDOWN    ),
            ('visualization', VIS_ID__TOP_HOURLY_PARTITIONS      )]

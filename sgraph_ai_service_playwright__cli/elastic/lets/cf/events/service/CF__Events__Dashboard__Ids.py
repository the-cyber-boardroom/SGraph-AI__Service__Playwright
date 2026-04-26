# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — CF__Events__Dashboard__Ids
# Slice-2 mirror of slice 1's CF__Inventory__Dashboard__Ids.  Single source of
# truth for the "CloudFront Logs - Events Overview" dashboard saved-object ids.
# Imported by both Events__Wiper (Phase 5, deletes them) and the future
# CF__Events__Dashboard__Builder (Phase 6, creates them with the same ids).
# ═══════════════════════════════════════════════════════════════════════════════


DASHBOARD_ID    = 'sg-cf-events-overview'                                            # Saved-object id of the events dashboard
DASHBOARD_TITLE = 'CloudFront Logs - Events Overview'                                # User-visible title

VIS_ID__STATUS_OVER_TIME    = 'sg-cf-evt-vis-status-over-time'                       # Panel 1 — stacked bar, count() over date_histogram(timestamp), split by terms(sc_status_class)
VIS_ID__EDGE_RESULT          = 'sg-cf-evt-vis-edge-result'                            # Panel 2 — donut, terms(x_edge_result_type)
VIS_ID__TOP_URIS             = 'sg-cf-evt-vis-top-uris'                               # Panel 3 — horizontal bar, terms(cs_uri_stem) top 25
VIS_ID__GEOGRAPHIC           = 'sg-cf-evt-vis-geographic'                             # Panel 4 — donut, terms(c_country)
VIS_ID__LATENCY_PERCENTILES  = 'sg-cf-evt-vis-latency-percentiles'                    # Panel 5 — line, percentiles(time_taken_ms) over date_histogram(timestamp)
VIS_ID__BOT_VS_HUMAN         = 'sg-cf-evt-vis-bot-vs-human'                           # Panel 6 — stacked bar, count() over date_histogram(timestamp), split by terms(bot_category)


def all_events_dashboard_refs() -> list:                                             # Tuples consumed by Kibana__Saved_Objects__Client.delete_saved_objects
    return [('dashboard'    , DASHBOARD_ID                  ),
            ('visualization', VIS_ID__STATUS_OVER_TIME      ),
            ('visualization', VIS_ID__EDGE_RESULT           ),
            ('visualization', VIS_ID__TOP_URIS              ),
            ('visualization', VIS_ID__GEOGRAPHIC            ),
            ('visualization', VIS_ID__LATENCY_PERCENTILES   ),
            ('visualization', VIS_ID__BOT_VS_HUMAN          )]

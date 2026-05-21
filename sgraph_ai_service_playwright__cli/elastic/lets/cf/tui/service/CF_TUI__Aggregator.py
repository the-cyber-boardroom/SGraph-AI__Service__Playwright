# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Aggregator
# PURE: a sequence of parsed Schema__CF__Event__Record → one Schema__CF_TUI__Traffic
# _Snapshot. This is the Extract/Transform of the live view done in-memory — no
# Elasticsearch in the loop (the seam the brief calls for). Every tally counts real
# parsed records; with no records the snapshot is all-zero, never fabricated.
# No textual, no rich, no boto3 — runs on 3.11 and is fully unit-testable.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Bot__Category   import Enum__CF__Bot__Category
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.enums.Enum__CF__Status__Class   import Enum__CF__Status__Class
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.enums.Enum__CF_TUI__Source         import Enum__CF_TUI__Source
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Count_Row  import Schema__CF_TUI__Count_Row
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Series_Point import Schema__CF_TUI__Series_Point
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Traffic_Snapshot import Schema__CF_TUI__Traffic_Snapshot
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config            import TUI_TOP_N

STATUS_LABEL = {Enum__CF__Status__Class.INFORMATIONAL: '1xx',
                Enum__CF__Status__Class.SUCCESS      : '2xx',
                Enum__CF__Status__Class.REDIRECTION  : '3xx',
                Enum__CF__Status__Class.CLIENT_ERROR : '4xx',
                Enum__CF__Status__Class.SERVER_ERROR : '5xx',
                Enum__CF__Status__Class.OTHER        : 'other'}

STATUS_ORDER = ['1xx', '2xx', '3xx', '4xx', '5xx', 'other']                          # canonical render order (only non-zero classes are emitted)


class CF_TUI__Aggregator(Type_Safe):
    top_n : int = TUI_TOP_N

    def aggregate(self, records,
                        source        : Enum__CF_TUI__Source = Enum__CF_TUI__Source.IN_MEMORY,
                        source_label  : str = '',
                        files_sampled : int = 0,
                        lines_skipped : int = 0,
                        captured_at   : int = 0) -> Schema__CF_TUI__Traffic_Snapshot:
        snapshot = Schema__CF_TUI__Traffic_Snapshot(source        = source,
                                                    source_label  = source_label,
                                                    files_sampled = files_sampled,
                                                    lines_skipped = lines_skipped,
                                                    captured_at   = captured_at or int(time.time()))
        uri_counts     = {}
        country_counts = {}
        bot_counts     = {}
        status_counts  = {}
        minute_counts  = {}

        for record in records:
            snapshot.total_events += 1

            if   record.bot_category == Enum__CF__Bot__Category.HUMAN  : snapshot.human_events   += 1
            elif record.bot_category == Enum__CF__Bot__Category.UNKNOWN: snapshot.unknown_events += 1
            else                                                       : snapshot.bot_events     += 1   # BOT_KNOWN / BOT_GENERIC

            if record.cache_hit: snapshot.cache_hits  += 1
            else               : snapshot.cache_other += 1

            uri = str(record.cs_uri_stem)
            if uri:
                uri_counts[uri] = uri_counts.get(uri, 0) + 1

            country = str(record.c_country)
            if country:
                country_counts[country] = country_counts.get(country, 0) + 1

            if record.is_bot:
                ua = str(record.cs_user_agent)[:38] or '(empty UA)'
                bot_counts[ua] = bot_counts.get(ua, 0) + 1

            status_label = STATUS_LABEL.get(record.sc_status_class, 'other')
            status_counts[status_label] = status_counts.get(status_label, 0) + 1

            minute = str(record.timestamp)[11:16]                                    # "HH:MM" from the ISO timestamp
            if minute:
                minute_counts[minute] = minute_counts.get(minute, 0) + 1

        self.fill_top_n(snapshot.top_uris,      uri_counts)
        self.fill_top_n(snapshot.top_countries, country_counts)
        self.fill_top_n(snapshot.top_bots,      bot_counts)

        for label in STATUS_ORDER:                                                   # canonical order; only classes that occurred
            if status_counts.get(label):
                snapshot.status_classes.append(Schema__CF_TUI__Count_Row(label=label, count=status_counts[label]))

        for minute in sorted(minute_counts):                                         # chronological buckets for the sparkline
            snapshot.throughput.append(Schema__CF_TUI__Series_Point(label=minute, value=minute_counts[minute]))

        return snapshot

    def fill_top_n(self, target_list, counts : dict) -> None:                        # highest count first; label as tie-breaker for determinism
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        for label, count in ranked[:self.top_n]:
            target_list.append(Schema__CF_TUI__Count_Row(label=label, count=count))

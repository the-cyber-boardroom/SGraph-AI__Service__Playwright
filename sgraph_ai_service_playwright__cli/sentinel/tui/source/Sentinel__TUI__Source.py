# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Source
# The data layer behind every Sentinel TUI surface — the structured, chatbot-ready
# seam the screens (and a future chat provider) read. Wraps an injectable Log__Sink
# (defaults to the local-FS sink) plus the rule registry and the L1 engine source.
# No textual, no I/O beyond the sink/registry it composes; tests inject an in-memory
# sink (no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.sentinel.collections.List__Schema__Sentinel__Log_Record import List__Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.rules.Sentinel__Rule__Registry                 import Sentinel__Rule__Registry
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source            import Sentinel__L1__Source, node_available
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record           import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Log__Sink                      import Log__Sink
from sgraph_ai_service_playwright__cli.sentinel.tui.schemas.List__Schema__Sentinel__TUI__Block_Group import List__Schema__Sentinel__TUI__Block_Group
from sgraph_ai_service_playwright__cli.sentinel.tui.schemas.Schema__Sentinel__TUI__Block_Group      import Schema__Sentinel__TUI__Block_Group
from sgraph_ai_service_playwright__cli.sentinel.tui.schemas.Schema__Sentinel__TUI__Status           import Schema__Sentinel__TUI__Status


def _is_block(record: Schema__Sentinel__Log_Record) -> bool:
    return record.verdict.value == 'block'


class Sentinel__TUI__Source(Type_Safe):
    log_sink  : Log__Sink
    l1_source : Sentinel__L1__Source

    # ── rules ────────────────────────────────────────────────────────────────
    def rules(self):
        return Sentinel__Rule__Registry().all()

    def rule(self, rule_id: str):
        return Sentinel__Rule__Registry().get(rule_id)

    # ── logs ─────────────────────────────────────────────────────────────────
    def records(self) -> List__Schema__Sentinel__Log_Record:
        return self.log_sink.read_all()

    def record(self, request_id: str):
        return self.log_sink.get(request_id)

    # ── blocks ───────────────────────────────────────────────────────────────
    def blocks(self) -> List__Schema__Sentinel__Log_Record:
        out = List__Schema__Sentinel__Log_Record()
        for record in self.records():
            if _is_block(record):
                out.append(record)
        return out

    def block_groups(self) -> List__Schema__Sentinel__TUI__Block_Group:             # aggregated by (rule, reason, action), count desc
        by_rule = {}
        for record in self.blocks():
            key = str(record.rule_id)
            grp = by_rule.get(key)
            if grp is None:
                grp = Schema__Sentinel__TUI__Block_Group(reason=str(record.reason), rule_id=str(record.rule_id),
                                                         layer=record.layer, action=record.action, count=0)
                by_rule[key] = grp
            grp.count += 1
        groups = List__Schema__Sentinel__TUI__Block_Group()
        for grp in sorted(by_rule.values(), key=lambda g: (-g.count, str(g.rule_id))):
            groups.append(grp)
        return groups

    # ── engine / status ───────────────────────────────────────────────────────
    def engine_code(self) -> str:
        return self.l1_source.materialised_source()

    def _engine_const(self, name: str) -> str:
        m = re.search(rf"var {name}\s*=\s*'([^']*)'", self.l1_source.raw_source())
        return m.group(1) if m else ''

    def status(self) -> Schema__Sentinel__TUI__Status:
        records = self.records()
        blocks  = [r for r in records if _is_block(r)]
        return Schema__Sentinel__TUI__Status(node_available  = node_available(),
                                             record_count    = len(records),
                                             allow_count     = len(records) - len(blocks),
                                             block_count     = len(blocks),
                                             rule_count      = len(self.rules()),
                                             banned_ip_count = len(self.l1_source.banned_ips()),
                                             engine_version  = self._engine_const('ENGINE_VERSION'),
                                             ruleset_version = self._engine_const('RULESET_VERSION'))

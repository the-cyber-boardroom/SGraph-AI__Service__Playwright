# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Tui_Api__Provider
# SG/Sentinel as a TUI API — the structured, chatbot-addressable surface (the same
# data the TUIs render). Mirrors SG_Edge__Tui_Api__Provider. Owns NO logic: every
# action delegates to the injected Sentinel__TUI__Source (reads) or the node-backed
# generator (rules_test / traffic_gen — in-process L1/L2, no AWS, no persistence).
#
# READ-ONLY by decision: this provider exposes only read actions. Mutating surfaces
# (deploy_*, traffic_send over HTTP egress) are intentionally NOT registered here —
# the chat can inspect everything but changes nothing.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Change_Kind     import Enum__Tui_Api__Change_Kind
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier            import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Action         import List__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Tier           import List__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action       import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Manifest     import Schema__Tui_Api__Manifest
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Orientation  import Schema__Tui_Api__Orientation
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result       import Schema__Tui_Api__Result
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope        import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Skills       import Schema__Tui_Api__Skills
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Change_Log           import Tui_Api__Change_Log
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Provider             import Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Schema__Builder      import Tui_Api__Schema__Builder
from sgraph_ai_service_playwright__cli.sentinel.tui.source.Sentinel__TUI__Source          import Sentinel__TUI__Source
from sgraph_ai_service_playwright__cli.sentinel.tui.tui_api.schemas.Schema__Sentinel__Tui_Api__Params__Needle   import Schema__Sentinel__Tui_Api__Params__Needle
from sgraph_ai_service_playwright__cli.sentinel.tui.tui_api.schemas.Schema__Sentinel__Tui_Api__Params__Repeat   import Schema__Sentinel__Tui_Api__Params__Repeat
from sgraph_ai_service_playwright__cli.sentinel.tui.tui_api.schemas.Schema__Sentinel__Tui_Api__Params__Request  import Schema__Sentinel__Tui_Api__Params__Request
from sgraph_ai_service_playwright__cli.sentinel.tui.tui_api.schemas.Schema__Sentinel__Tui_Api__Params__Rule     import Schema__Sentinel__Tui_Api__Params__Rule

SLUG      = 'sg-sentinel'
TOOL      = 'sg-sentinel'
NO_ARGS   = {'type': 'object', 'properties': {}}
READ_ONLY = Enum__Tui_Api__Tier.READ_ONLY

_SKILL_API = (
    'SG/Sentinel read-only TUI API. Use these to answer questions about the edge guard.\n'
    'rules_list / rule_show{rule_id}: the 6 deterministic rules + metadata.\n'
    'logs_list / logs_trace{request_id}: records in the local sink (every observed request).\n'
    'blocks_list / blocks_why{needle}: blocked requests by reason/rule; why = lookup by request id or source IP.\n'
    'status / engine_code: deployment reality + the exact L1 engine that ships to CloudFront.\n'
    'traffic_cases / traffic_gen{repeat}: the use-case corpus + an in-process accuracy+latency run.\n'
    'All actions are read-only; nothing here changes state.')


def _read() -> Schema__Tui_Api__Scope:
    return Schema__Tui_Api__Scope(api=SLUG, capability='read')


class Sentinel__Tui_Api__Provider(Tui_Api__Provider):
    source  : Sentinel__TUI__Source
    builder : Tui_Api__Schema__Builder

    # ── contract ────────────────────────────────────────────────────────────────
    def manifest(self) -> Schema__Tui_Api__Manifest:
        rule_schema    = self.builder.input_schema(Schema__Sentinel__Tui_Api__Params__Rule)
        request_schema = self.builder.input_schema(Schema__Sentinel__Tui_Api__Params__Request)
        needle_schema  = self.builder.input_schema(Schema__Sentinel__Tui_Api__Params__Needle)
        repeat_schema  = self.builder.input_schema(Schema__Sentinel__Tui_Api__Params__Repeat)
        read           = _read()

        actions = List__Tui_Api__Action()
        def add(name, desc, schema=NO_ARGS):
            actions.append(Schema__Tui_Api__Action(name=name, tier=READ_ONLY, scope=read,
                                                   description=desc, input_schema=schema))
        add('rules_list',    'List the six deterministic MVP rules (id, name, action, layer, ATT&CK tag).')
        add('rule_show',     'Show one rule\'s metadata (schema in/out, confidence, attack tag).', rule_schema)
        add('rules_test',    'Run the L1 engine over the use-case corpus and show each verdict (needs node).')
        add('logs_list',     'Every log record in the sink (request id, verdict, rule, path).')
        add('logs_trace',    'The full replayable record for one request id.', request_schema)
        add('blocks_list',   'Blocked requests grouped by reason/rule with counts.')
        add('blocks_why',    'Explain why a request/IP was blocked (by request id or source IP, raw or hashed).', needle_schema)
        add('status',        'Reality: rule/banned-ip counts, sink record/allow/block counts, engine + ruleset version.')
        add('engine_code',   'The exact materialised L1 engine (sentinel_l1.js, BANNED_IPS inlined) that ships to CloudFront.')
        add('traffic_cases', 'The use-case traffic corpus (benign + malicious + malformed) with expected verdicts.')
        add('traffic_gen',   'Replay the corpus in-process through L1+L2: accuracy + latency report (needs node).', repeat_schema)

        tiers = List__Tui_Api__Tier()
        tiers.append(READ_ONLY)
        return Schema__Tui_Api__Manifest(slug=SLUG, tool=TOOL, name='SG/Sentinel (read-only)', version='0.1.0',
                                        description='Inspect the SG/Sentinel edge guard: rules, logs, blocks, status, engine code, traffic.',
                                        tiers=tiers, actions=actions, skills=Schema__Tui_Api__Skills())

    def state(self) -> dict:
        status = self.source.status()
        return {'node_available': status.node_available, 'record_count': status.record_count,
                'block_count': status.block_count, 'rule_count': status.rule_count}

    def orientation(self) -> Schema__Tui_Api__Orientation:
        log = Tui_Api__Change_Log()
        log.add(Enum__Tui_Api__Change_Kind.FEATURE,
                'SG/Sentinel read-only TUI API: rules/logs/blocks/status/engine/traffic.', '0.1.0')
        status = self.source.status()
        return Schema__Tui_Api__Orientation(tool=TOOL,
                                          status={'healthy': True, 'node': status.node_available,
                                                  'records': status.record_count},
                                          recent_changes=log.changes)

    def skills(self) -> dict:
        return {'api': _SKILL_API}

    # ── dispatch (delegate to the source / node-backed services) ────────────────
    def dispatch(self, action: str, params: dict) -> Schema__Tui_Api__Result:
        params = params or {}
        try:
            if   action == 'rules_list':
                data = {'rules': [r.json() for r in self.source.rules()]}
            elif action == 'rule_show':
                rule = self.source.rule(str(params.get('rule_id', '')))
                if rule is None:
                    return Schema__Tui_Api__Result(ok=False, error=f"no such rule: {params.get('rule_id', '')}")
                data = {'rule': rule.json()}
            elif action == 'rules_test':
                data = {'signals': self._run_corpus_signals()}
            elif action == 'logs_list':
                data = {'records': [r.json() for r in self.source.records()]}
            elif action == 'logs_trace':
                record = self.source.record(str(params.get('request_id', '')))
                if record is None:
                    return Schema__Tui_Api__Result(ok=False, error=f"no record: {params.get('request_id', '')}")
                data = {'record': record.json()}
            elif action == 'blocks_list':
                data = {'blocks': [g.json() for g in self.source.block_groups()]}
            elif action == 'blocks_why':
                data = {'matches': self._blocks_why(str(params.get('needle', '')))}
            elif action == 'status':
                data = {'status': self.source.status().json()}
            elif action == 'engine_code':
                data = {'engine_code': self.source.engine_code()}
            elif action == 'traffic_cases':
                from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Corpus import Sentinel__Traffic__Corpus
                data = {'cases': [c.json() for c in Sentinel__Traffic__Corpus().cases()]}
            elif action == 'traffic_gen':
                data = self._traffic_gen(int(params.get('repeat', 1) or 1))
            else:
                return Schema__Tui_Api__Result(ok=False, error=f'unknown action: {action}')
        except Exception as exc:                                                     # honest error, never a crash (e.g. node missing)
            return Schema__Tui_Api__Result(ok=False, error=f'{type(exc).__name__}: {exc}')
        return Schema__Tui_Api__Result(ok=True, data={'result': data})

    # ── node-backed helpers ──────────────────────────────────────────────────────
    def _generator(self):
        from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness  import Sentinel__Local__Harness
        from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink     import InMemory__Log__Sink
        from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Generator import Sentinel__Traffic__Generator
        return Sentinel__Traffic__Generator(harness=Sentinel__Local__Harness(log_sink=InMemory__Log__Sink()))

    def _run_corpus_signals(self) -> list:
        from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Corpus import Sentinel__Traffic__Corpus
        results = self._generator().run_local(Sentinel__Traffic__Corpus().cases())
        return [{'name': str(r.name), 'verdict': r.observed_verdict.value, 'rule': str(r.observed_rule)} for r in results]

    def _traffic_gen(self, repeat: int) -> dict:
        from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Corpus          import Sentinel__Traffic__Corpus
        from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Report__Builder import Sentinel__Traffic__Report__Builder
        results = self._generator().run_local(Sentinel__Traffic__Corpus().cases(), repeat=repeat)
        report  = Sentinel__Traffic__Report__Builder().build(results, mode='local')
        return {'report': report.json()}

    def _blocks_why(self, needle: str) -> list:
        import hashlib
        hashed = hashlib.sha256(needle.encode('utf-8')).hexdigest()[:12]
        out    = []
        for r in self.source.blocks():
            if needle in (str(r.request_id), str(r.source_ip)) or hashed == str(r.source_ip):
                out.append(r.json())
        return out

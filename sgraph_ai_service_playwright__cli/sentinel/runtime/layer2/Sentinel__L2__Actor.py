# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__L2__Actor
# The sole actor and sole I/O owner. Given a validated signal it: enforces the
# action (pass / 403 / 404), builds the log record, and writes it to the sink.
# Identical logic on AWS (Lambda@Edge) and locally — only the injected Log__Sink
# (and, on AWS, the transport that produced the signal) differs. It NEVER
# re-evaluates rules: L2 is a dumb actor in the tiny core.
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib

from osbot_utils.type_safe.Type_Safe                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Action            import Enum__Sentinel__Action
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Target            import Enum__Sentinel__Target
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict           import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Enforcement   import Schema__Sentinel__Enforcement
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record    import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Signal        import Schema__Sentinel__Signal
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Log__Sink              import Log__Sink


class Sentinel__L2__Actor(Type_Safe):
    log_sink     : Log__Sink
    privacy_mode : Safe_Str = Safe_Str('hash')                                      # 'hash' (default) | 'plain' | 'omit'

    def handle(self, signal : Schema__Sentinel__Signal,
                     target : Enum__Sentinel__Target) -> Schema__Sentinel__Enforcement:
        enforcement = self.enforce(signal)
        record      = self.build_record(signal, target, enforcement)
        self.log_sink.write(record)                                                 # L2 is the sole I/O owner
        return enforcement

    def enforce(self, signal: Schema__Sentinel__Signal) -> Schema__Sentinel__Enforcement:
        if signal.verdict == Enum__Sentinel__Verdict.BLOCK:
            if signal.action == Enum__Sentinel__Action.DEFLECT_404:
                return Schema__Sentinel__Enforcement(pass_to_origin=False, http_status=404)
            return     Schema__Sentinel__Enforcement(pass_to_origin=False, http_status=403)
        return         Schema__Sentinel__Enforcement(pass_to_origin=True,  http_status=0)

    def build_record(self, signal      : Schema__Sentinel__Signal,
                           target      : Enum__Sentinel__Target,
                           enforcement : Schema__Sentinel__Enforcement) -> Schema__Sentinel__Log_Record:
        captured = signal.captured
        return Schema__Sentinel__Log_Record(request_id      = str(signal.request_id),
                                            received_at     = str(captured.received_at),
                                            target          = target,
                                            method          = str(captured.method),
                                            path            = str(captured.path),
                                            host            = str(captured.host),
                                            source_ip       = self.privacy_ip(str(captured.source_ip)),
                                            user_agent      = str(captured.user_agent),
                                            verdict         = signal.verdict,
                                            reason          = str(signal.reason),
                                            rule_id         = str(signal.rule_id),
                                            action          = signal.action,
                                            layer           = signal.layer,
                                            enforced        = (not enforcement.pass_to_origin),
                                            http_status     = enforcement.http_status,
                                            engine_version  = str(signal.engine_version),
                                            ruleset_version = str(signal.ruleset_version))

    def privacy_ip(self, source_ip: str) -> str:
        mode = str(self.privacy_mode)
        if mode == 'omit' or source_ip == '':
            return ''
        if mode == 'plain':
            return source_ip
        return hashlib.sha256(source_ip.encode('utf-8')).hexdigest()[:12]            # 'hash' (default)

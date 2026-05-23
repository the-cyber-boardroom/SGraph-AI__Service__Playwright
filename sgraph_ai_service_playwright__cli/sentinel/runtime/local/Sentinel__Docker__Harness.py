# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Docker__Harness
# Target C driver: POSTs a captured request at the running CF-env sim container to
# get the L1 signal, then runs the SAME Python L2 actor on it. Mirrors the local-
# direct harness API (evaluate_signal / hit) so the parity matrix drives both the
# same way. Assumes the container is already up (sg sentinel local up --docker).
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Target            import Enum__Sentinel__Target
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer2.Sentinel__L2__Actor      import Sentinel__L2__Actor
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Docker__Runtime import Sentinel__Docker__Runtime
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness  import build_captured
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Signal        import Schema__Sentinel__Signal
from sgraph_ai_service_playwright__cli.sentinel.service.Signal__Codec                   import Signal__Codec
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Log__Sink              import Log__Sink


class Sentinel__Docker__Harness(Type_Safe):
    log_sink     : Log__Sink
    runtime      : Sentinel__Docker__Runtime
    privacy_mode : Safe_Str = Safe_Str('hash')

    def evaluate_signal(self, captured: dict) -> Schema__Sentinel__Signal:          # L1 via the container — no sink write
        sig_dict = self.runtime.evaluate(captured)
        return Signal__Codec().decode(json.dumps(sig_dict))

    def hit(self, method : str, path : str, source_ip : str = '', **kw):            # full stack: container L1 → L2 → sink
        captured    = build_captured(method, path, source_ip, **kw)
        signal      = self.evaluate_signal(captured)
        actor       = Sentinel__L2__Actor(log_sink=self.log_sink, privacy_mode=self.privacy_mode)
        enforcement = actor.handle(signal, Enum__Sentinel__Target.LOCAL_DOCKER)
        return signal, enforcement

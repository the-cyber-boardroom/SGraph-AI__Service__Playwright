# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Local__Harness
# The offline full stack (Target B, local-direct): the real L1 JS engine driven via
# node + the real Python L2 actor in-process, writing to a local sink. Only the
# transport (in-proc instead of a header) and the sink (local FS instead of S3)
# differ from what ships to AWS — the L1 engine and L2 logic are byte-/logic-
# identical. evaluate_signal() is pure (no write); hit() runs the full L2 path.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import secrets

from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Target            import Enum__Sentinel__Target
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source     import Sentinel__L1__Source
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer2.Sentinel__L2__Actor      import Sentinel__L2__Actor
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Enforcement   import Schema__Sentinel__Enforcement
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Signal        import Schema__Sentinel__Signal
from sgraph_ai_service_playwright__cli.sentinel.service.Signal__Codec                   import Signal__Codec
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Log__Sink              import Log__Sink


def default_local_sink_dir() -> str:                                                # stable location so logs/blocks read what hit wrote
    override = os.environ.get('SG_SENTINEL__LOCAL_SINK_DIR', '')                     # override (tests / custom layout)
    if override:
        return override
    return os.path.join(os.path.expanduser('~'), '.sg_sentinel', 'local-logs')


class Sentinel__Local__Harness(Type_Safe):
    log_sink     : Log__Sink
    l1_source    : Sentinel__L1__Source
    privacy_mode : Safe_Str = Safe_Str('hash')

    def build_captured(self, method      : str, path : str, source_ip : str = '',
                             host        : str = 'static.example.com',
                             user_agent  : str = 'sentinel-local',
                             querystring : str = '',
                             request_id  : str = '', received_at : str = '') -> dict:
        rid = request_id  or ('sn-' + secrets.token_hex(12))
        ts  = received_at or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        return {'request_id'  : rid, 'aws_request_id': '', 'method': method, 'path': path,
                'querystring' : querystring, 'host': host, 'source_ip': source_ip,
                'user_agent'  : user_agent, 'received_at': ts, 'cache_status': 'miss'}

    def evaluate_signal(self, captured: dict) -> Schema__Sentinel__Signal:          # L1 only — no I/O, no sink write
        sig_dict = self.l1_source.evaluate(captured)
        return Signal__Codec().decode(json.dumps(sig_dict))

    def hit(self, method : str, path : str, source_ip : str = '', **kw):            # full stack: L1 → L2 → sink
        captured    = self.build_captured(method, path, source_ip, **kw)
        signal      = self.evaluate_signal(captured)
        actor       = Sentinel__L2__Actor(log_sink=self.log_sink, privacy_mode=self.privacy_mode)
        enforcement = actor.handle(signal, Enum__Sentinel__Target.LOCAL_DIRECT)
        return signal, enforcement

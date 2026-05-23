# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Sentinel__L2__Actor (enforce + build_record + write)
# No node here — signals are constructed directly; this isolates L2 logic.
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Action          import Enum__Sentinel__Action
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Target          import Enum__Sentinel__Target
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict         import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.runtime.layer2.Sentinel__L2__Actor    import Sentinel__L2__Actor
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Captured    import Schema__Sentinel__Captured
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Signal      import Schema__Sentinel__Signal
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink  import InMemory__Log__Sink


def _signal(verdict, action, source_ip='185.10.10.10', rule_id='0012', reason='path never valid') -> Schema__Sentinel__Signal:
    captured = Schema__Sentinel__Captured(method='GET', path='/etc/passwd', host='h',
                                          source_ip=source_ip, user_agent='ua',
                                          received_at='2026-05-23T14:30:00Z', cache_status='miss')
    return Schema__Sentinel__Signal(request_id='sn-1', captured=captured, verdict=verdict,
                                    reason=reason, rule_id=rule_id, action=action,
                                    engine_version='0.1.0', ruleset_version='0.1.0')


def _actor(privacy_mode='hash') -> Sentinel__L2__Actor:
    return Sentinel__L2__Actor(log_sink=InMemory__Log__Sink(), privacy_mode=privacy_mode)


class TestEnforce:
    def test_drop_403_blocks_with_403(self):
        e = _actor().enforce(_signal(Enum__Sentinel__Verdict.BLOCK, Enum__Sentinel__Action.DROP_403))
        assert e.pass_to_origin is False and e.http_status == 403

    def test_deflect_404_blocks_with_404(self):
        e = _actor().enforce(_signal(Enum__Sentinel__Verdict.BLOCK, Enum__Sentinel__Action.DEFLECT_404))
        assert e.pass_to_origin is False and e.http_status == 404

    def test_allow_passes_to_origin(self):
        e = _actor().enforce(_signal(Enum__Sentinel__Verdict.ALLOW, Enum__Sentinel__Action.PASS))
        assert e.pass_to_origin is True and e.http_status == 0


class TestHandleWritesRecord:
    def test_block_writes_enforced_record_with_reason(self):
        actor = _actor()
        actor.handle(_signal(Enum__Sentinel__Verdict.BLOCK, Enum__Sentinel__Action.DROP_403),
                     Enum__Sentinel__Target.LOCAL_DIRECT)
        rec = actor.log_sink.read_all()[0]
        assert rec.verdict       == Enum__Sentinel__Verdict.BLOCK
        assert rec.enforced      is True
        assert rec.http_status   == 403
        assert str(rec.reason)   == 'path never valid'
        assert rec.target        == Enum__Sentinel__Target.LOCAL_DIRECT

    def test_allow_writes_unenforced_record(self):
        actor = _actor()
        actor.handle(_signal(Enum__Sentinel__Verdict.ALLOW, Enum__Sentinel__Action.PASS, rule_id='0001', reason='no rule matched'),
                     Enum__Sentinel__Target.LOCAL_DIRECT)
        rec = actor.log_sink.read_all()[0]
        assert rec.enforced is False
        assert rec.http_status == 0


class TestPrivacyMode:
    def test_hash_mode_hashes_source_ip(self):
        actor = _actor('hash')
        actor.handle(_signal(Enum__Sentinel__Verdict.ALLOW, Enum__Sentinel__Action.PASS, source_ip='1.2.3.4'),
                     Enum__Sentinel__Target.LOCAL_DIRECT)
        rec = actor.log_sink.read_all()[0]
        assert str(rec.source_ip) == hashlib.sha256(b'1.2.3.4').hexdigest()[:12]
        assert str(rec.source_ip) != '1.2.3.4'

    def test_plain_mode_keeps_source_ip(self):
        actor = _actor('plain')
        actor.handle(_signal(Enum__Sentinel__Verdict.ALLOW, Enum__Sentinel__Action.PASS, source_ip='1.2.3.4'),
                     Enum__Sentinel__Target.LOCAL_DIRECT)
        assert str(actor.log_sink.read_all()[0].source_ip) == '1.2.3.4'

    def test_omit_mode_drops_source_ip(self):
        actor = _actor('omit')
        actor.handle(_signal(Enum__Sentinel__Verdict.ALLOW, Enum__Sentinel__Action.PASS, source_ip='1.2.3.4'),
                     Enum__Sentinel__Target.LOCAL_DIRECT)
        assert str(actor.log_sink.read_all()[0].source_ip) == ''

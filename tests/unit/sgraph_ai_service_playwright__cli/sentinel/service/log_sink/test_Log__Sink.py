# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for the Log__Sink family (key layout + InMemory + Local_FS)
# Local_FS and InMemory must agree on the key layout and round-trip records.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import tempfile

from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink  import InMemory__Log__Sink
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Local_FS__Log__Sink   import Local_FS__Log__Sink


def _record(request_id='sn-1', received_at='2026-05-23T14:30:00Z', path='/etc/passwd', verdict='block') -> Schema__Sentinel__Log_Record:
    return Schema__Sentinel__Log_Record(request_id=request_id, received_at=received_at,
                                        method='GET', path=path, host='h', source_ip='abc123',
                                        verdict=verdict, reason='path never valid', rule_id='0012')


class TestKeyLayout:
    def test_key_follows_yyyy_mm_dd_hh_layout(self):
        key = InMemory__Log__Sink().key_for(_record())
        assert key == 'sentinel/2026/05/23/14/sn-1.json'

    def test_local_fs_and_in_memory_agree_on_key(self):
        rec = _record()
        assert Local_FS__Log__Sink(root_dir='/tmp/x').key_for(rec) == InMemory__Log__Sink().key_for(rec)


class TestInMemorySink:
    def test_write_then_read_all(self):
        sink = InMemory__Log__Sink()
        sink.write(_record(request_id='sn-a'))
        sink.write(_record(request_id='sn-b'))
        assert len(sink.read_all()) == 2

    def test_get_by_request_id(self):
        sink = InMemory__Log__Sink()
        sink.write(_record(request_id='sn-a', path='/a'))
        sink.write(_record(request_id='sn-b', path='/b'))
        assert str(sink.get('sn-b').path) == '/b'
        assert sink.get('sn-missing') is None


class TestLocalFsSink:
    def test_write_creates_object_and_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            sink = Local_FS__Log__Sink(root_dir=d)
            key  = sink.write(_record(request_id='sn-fs'))
            assert key.endswith('sn-fs.json')
            back = sink.read_all()
            assert len(back) == 1
            assert str(back[0].path)    == '/etc/passwd'
            assert str(back[0].rule_id) == '0012'

    def test_read_all_empty_when_dir_absent(self):
        sink = Local_FS__Log__Sink(root_dir='/tmp/sg_sentinel_does_not_exist_xyz')
        assert len(sink.read_all()) == 0

    def test_root_dir_path_is_not_mangled(self):                                     # regression: Safe_Str used to turn '/' '.' '-' into '_'
        with tempfile.TemporaryDirectory() as d:
            root = os.path.join(d, 'SGraph-AI__Service__Playwright', '_vaults', 'sentinel')   # slashes, dots, hyphens
            sink = Local_FS__Log__Sink(root_dir=root)
            assert sink.root_dir == root                                            # preserved verbatim
            sink.write(_record(request_id='sn-fs'))
            assert os.path.isdir(os.path.join(root, 'sentinel'))                    # wrote UNDER the real absolute path
            assert len(sink.read_all()) == 1

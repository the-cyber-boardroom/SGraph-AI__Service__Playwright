# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Log__Sink
# Base for the L2 log sink. Defines the shared key layout — identical across S3 and
# local FS so `trace`/replay behave the same everywhere:
#     <prefix>/YYYY/MM/DD/HH/<request_id>.json   (one object per record; batching deferred)
# Subclasses implement write() + read_all(); the base derives key_for() and get().
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str

from sgraph_ai_service_playwright__cli.sentinel.collections.List__Schema__Sentinel__Log_Record import List__Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record           import Schema__Sentinel__Log_Record


class Log__Sink(Type_Safe):
    prefix : Safe_Str = Safe_Str('sentinel')

    def key_for(self, record: Schema__Sentinel__Log_Record) -> str:
        ts = str(record.received_at)                                                # 'YYYY-MM-DDTHH:MM:SSZ'
        y, m, d, h = (ts[0:4] or '0000'), (ts[5:7] or '00'), (ts[8:10] or '00'), (ts[11:13] or '00')
        return f'{str(self.prefix)}/{y}/{m}/{d}/{h}/{str(record.request_id)}.json'

    def write(self, record: Schema__Sentinel__Log_Record) -> str:                   # returns the key written
        raise NotImplementedError

    def read_all(self) -> List__Schema__Sentinel__Log_Record:
        raise NotImplementedError

    def get(self, request_id: str) -> Schema__Sentinel__Log_Record:                 # None when not found
        for record in self.read_all():
            if str(record.request_id) == str(request_id):
                return record
        return None

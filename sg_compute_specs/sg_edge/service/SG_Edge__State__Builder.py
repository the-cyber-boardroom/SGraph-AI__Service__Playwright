# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: SG_Edge__State__Builder
# Composes and parses the _state.<parent> TXT record — the Edge Waker's only
# piece of state, held in DNS (brief 02). Wire form is key=value;key=value under
# the 255-char DNS TXT limit, e.g. "zero_streak=2;updated=1747700000".
#
# Mirrors SG_Edge__TXT__Builder but for the teardown counter rather than the
# routing record. Read on every idle-check, written (UPSERT) when the counter
# changes. Concurrent writers are tolerated — last-write-wins is fine because the
# counter only needs to be approximately right. Pure logic — no AWS, no I/O.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

from osbot_utils.type_safe.Type_Safe                                         import Type_Safe

from sg_compute_specs.sg_edge.primitives.Safe_Int__SG_Edge__Cycle_Count      import Safe_Int__SG_Edge__Cycle_Count
from sg_compute_specs.sg_edge.primitives.Safe_Int__SG_Edge__Unix_Ts          import Safe_Int__SG_Edge__Unix_Ts
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__State__Record         import Schema__SG_Edge__State__Record

MAX_TXT_LENGTH = 255                                                           # DNS TXT character-string limit
FIELD_SEP      = ';'
KV_SEP         = '='
REQUIRED_KEYS  = ('zero_streak', 'updated')


class SG_Edge__State__Builder(Type_Safe):

    def build(self, record : Schema__SG_Edge__State__Record) -> str:           # schema -> wire string
        txt = FIELD_SEP.join([f'zero_streak{KV_SEP}{int(record.zero_streak)}',
                              f'updated{KV_SEP}{int(record.updated)}'        ])
        if len(txt) > MAX_TXT_LENGTH:                                          # boundary guard — DNS would reject it
            raise ValueError(f'state record exceeds {MAX_TXT_LENGTH} chars: {len(txt)}')
        return txt

    def parse(self, txt : str) -> Schema__SG_Edge__State__Record:              # wire string -> schema; raises on invalid
        fields = self._split(txt)
        for key in REQUIRED_KEYS:
            if key not in fields:
                raise ValueError(f'state record missing required field: {key}')
        return Schema__SG_Edge__State__Record(zero_streak = Safe_Int__SG_Edge__Cycle_Count(int(fields['zero_streak'])),
                                              updated     = Safe_Int__SG_Edge__Unix_Ts(int(fields['updated'])))

    def try_parse(self, txt : str) -> Optional[Schema__SG_Edge__State__Record]:  # None instead of raising
        try:
            return self.parse(txt)
        except (ValueError, KeyError):
            return None

    def _split(self, txt : str) -> dict:                                       # "a=1;b=2" -> {'a':'1','b':'2'}
        out = {}
        for segment in (txt or '').split(FIELD_SEP):
            segment = segment.strip()
            if not segment:
                continue
            if KV_SEP not in segment:
                raise ValueError(f'malformed state segment (no {KV_SEP!r}): {segment!r}')
            key, value = segment.split(KV_SEP, 1)
            out[key.strip()] = value.strip()
        return out

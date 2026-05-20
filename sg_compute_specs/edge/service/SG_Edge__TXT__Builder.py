# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — edge: SG_Edge__TXT__Builder
# Composes and parses the _sg.<slug> routing TXT record (brief 03). Wire form is
# a flat key=value;key=value string kept under the 255-char DNS TXT limit:
#
#   v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1747700000;instance=i-0abc...
#
# Deliberately NOT JSON — the brief wants it debuggable straight from `dig`
# output. This builder is the single shared composer/parser used by both the
# Vault Waker (on provision) and the Vault Reaper (on orphan scan), so the wire
# format lives in exactly one place. Pure logic — no AWS, no I/O.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

from osbot_utils.type_safe.Type_Safe                                         import Type_Safe

from sg_compute.primitives.Safe_Str__IP__Address                            import Safe_Str__IP__Address
from sg_compute.primitives.Safe_Int__Port                                   import Safe_Int__Port
from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id             import Safe_Str__Instance__Id
from sg_compute_specs.edge.enums.Enum__Edge__Backend__Type                  import Enum__Edge__Backend__Type
from sg_compute_specs.edge.primitives.Safe_Int__Edge__TXT_Version           import Safe_Int__Edge__TXT_Version
from sg_compute_specs.edge.primitives.Safe_Int__Edge__Unix_Ts               import Safe_Int__Edge__Unix_Ts
from sg_compute_specs.edge.schemas.Schema__Edge__TXT__Record                import Schema__Edge__TXT__Record

SUPPORTED_VERSION = 1                                                          # only v=1 exists today
MAX_TXT_LENGTH    = 255                                                        # DNS TXT character-string limit
FIELD_SEP         = ';'
KV_SEP            = '='
REQUIRED_KEYS     = ('v', 'ip', 'port', 'type', 'launched')                    # `instance` is optional


class SG_Edge__TXT__Builder(Type_Safe):

    # ── compose ───────────────────────────────────────────────────────────────

    def build(self, record : Schema__Edge__TXT__Record) -> str:                # schema -> wire string
        parts = [f'v{KV_SEP}{int(record.version)}'             ,
                 f'ip{KV_SEP}{record.ip}'                      ,
                 f'port{KV_SEP}{int(record.port)}'             ,
                 f'type{KV_SEP}{record.type}'                  ,
                 f'launched{KV_SEP}{int(record.launched)}'     ]
        if record.instance:                                                    # optional — omitted when unset
            parts.append(f'instance{KV_SEP}{record.instance}')
        txt = FIELD_SEP.join(parts)
        if len(txt) > MAX_TXT_LENGTH:                                          # boundary guard — DNS would reject it
            raise ValueError(f'TXT record exceeds {MAX_TXT_LENGTH} chars: {len(txt)}')
        return txt

    # ── parse ───────────────────────────────────────────────────────────────

    def parse(self, txt : str) -> Schema__Edge__TXT__Record:                   # wire string -> schema; raises on invalid
        fields = self._split(txt)
        for key in REQUIRED_KEYS:
            if key not in fields:
                raise ValueError(f'TXT record missing required field: {key}')

        version = int(fields['v'])
        if version != SUPPORTED_VERSION:
            raise ValueError(f'unsupported TXT version: {version}')

        record = Schema__Edge__TXT__Record(version  = Safe_Int__Edge__TXT_Version(version)        ,
                                           ip       = Safe_Str__IP__Address(fields['ip'])         ,
                                           port     = Safe_Int__Port(int(fields['port']))         ,
                                           type     = Enum__Edge__Backend__Type(fields['type'])   ,
                                           launched = Safe_Int__Edge__Unix_Ts(int(fields['launched'])))
        if fields.get('instance'):                                             # optional
            record.instance = Safe_Str__Instance__Id(fields['instance'])
        return record

    def try_parse(self, txt : str) -> Optional[Schema__Edge__TXT__Record]:     # hot-path variant — None instead of raising
        try:
            return self.parse(txt)
        except (ValueError, KeyError):
            return None

    def is_valid(self, txt : str) -> bool:                                     # cheap predicate over try_parse
        return self.try_parse(txt) is not None

    # ── internal ──────────────────────────────────────────────────────────────

    def _split(self, txt : str) -> dict:                                       # "a=1;b=2" -> {'a':'1','b':'2'}
        out = {}
        for segment in (txt or '').split(FIELD_SEP):
            segment = segment.strip()
            if not segment:
                continue
            if KV_SEP not in segment:
                raise ValueError(f'malformed TXT segment (no {KV_SEP!r}): {segment!r}')
            key, value = segment.split(KV_SEP, 1)
            out[key.strip()] = value.strip()
        return out

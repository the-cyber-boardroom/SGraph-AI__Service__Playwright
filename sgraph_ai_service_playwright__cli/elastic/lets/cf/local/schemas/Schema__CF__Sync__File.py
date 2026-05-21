# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf local: Schema__CF__Sync__File
# One S3 object in a sync plan: its key, the local path it maps to, size, and whether
# it is already present locally. CF logs are immutable, so present_local=True means
# "done, never re-fetch". Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF__Sync__File(Type_Safe):
    key           : str
    local_path    : str
    size          : int  = 0
    last_modified : str
    present_local : bool = False

# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf local: CF__Local__Store
# The local raw-cf-logs cache on disk. Maps an S3 key to a local path by stripping the
# CF_LOGS_PREFIX so the partition layout (YYYY/MM/DD/HH/file) is preserved under
# _vaults/cf-logs/{data-type}/, reads/writes those files, and rolls the tree up into
# Schema__CF__Local__Stats. `root` is injectable so tests point it at a tmp dir — the
# default resolves to the gitignored repo vault. Plain fs — no AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib import Path

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.cf_local__config       import CF_LOGS_DATA_TYPE_RAW, vaults_cf_logs_root
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Local__Day_Stat import Schema__CF__Local__Day_Stat
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Local__Stats    import Schema__CF__Local__Stats
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config           import CF_LOGS_PREFIX


class CF__Local__Store(Type_Safe):
    root       : str = ''                                                            # '' → repo _vaults/cf-logs ; tests inject a tmp dir
    data_type  : str = CF_LOGS_DATA_TYPE_RAW
    src_prefix : str = CF_LOGS_PREFIX                                                # stripped from S3 keys to form the relative path

    def base_dir(self) -> Path:
        base = Path(self.root) if self.root else vaults_cf_logs_root()
        return base / self.data_type

    def rel_for_key(self, key : str) -> str:
        k = key
        if k.startswith(self.src_prefix):
            k = k[len(self.src_prefix):]
        return k.lstrip('/')

    def local_path_for_key(self, key : str) -> Path:
        return self.base_dir() / self.rel_for_key(key)

    def has_key(self, key : str) -> bool:
        return self.local_path_for_key(key).is_file()

    def write_key(self, key : str, data : bytes) -> Path:
        path = self.local_path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def read_key(self, key : str) -> bytes:
        path = self.local_path_for_key(key)
        return path.read_bytes() if path.is_file() else b''

    def iter_local_files(self) -> list:
        base = self.base_dir()
        if not base.exists():
            return []
        return sorted(p for p in base.rglob('*') if p.is_file())

    def stats(self) -> Schema__CF__Local__Stats:
        base  = self.base_dir()
        stats = Schema__CF__Local__Stats(data_type=self.data_type, base_path=str(base), exists=base.exists())
        if not base.exists():
            return stats
        per_day = {}                                                                 # day → {files, bytes, hours:set}
        for path in self.iter_local_files():
            rel   = path.relative_to(base).as_posix()                                # YYYY/MM/DD/HH/file
            parts = rel.split('/')
            size  = path.stat().st_size
            stats.total_files += 1
            stats.total_bytes += size
            if len(parts) >= 3:
                day  = '/'.join(parts[:3])
                hour = parts[3] if len(parts) >= 5 else ''
                slot = per_day.setdefault(day, {'files': 0, 'bytes': 0, 'hours': set()})
                slot['files'] += 1
                slot['bytes'] += size
                if hour:
                    slot['hours'].add(hour)
        for day in sorted(per_day):
            slot = per_day[day]
            stats.days.append(Schema__CF__Local__Day_Stat(day=day, files=slot['files'], bytes=slot['bytes'], hours=len(slot['hours'])))
        stats.day_count  = len(stats.days)
        stats.hour_count = sum(d.hours for d in stats.days)
        if stats.days:
            stats.first_day = stats.days[0].day
            stats.last_day  = stats.days[-1].day
        return stats

# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf local: cf_local__config
# Where the local raw-cf-logs cache lives and how it is laid out. The cache mirrors
# the S3 partition under a gitignored vault folder:
#     _vaults/cf-logs/{data-type}/{YYYY}/{MM}/{DD}/{HH}/{file}
# data-type 'raw-cf-logs' is an exact byte copy of what S3 holds (the Firehose .gz
# objects). Other data-types (parsed, enriched, …) will sit alongside it later.
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib import Path

CF_LOGS_DATA_TYPE_RAW = 'raw-cf-logs'                                                # exact copy of the S3 Firehose objects


def repo_root() -> Path:                                                             # .../cf/local/cf_local__config.py → repo root is 5 parents up
    return Path(__file__).resolve().parents[5]


def vaults_cf_logs_root() -> Path:                                                   # gitignored (.gitignore: _vaults)
    return repo_root() / '_vaults' / 'cf-logs'

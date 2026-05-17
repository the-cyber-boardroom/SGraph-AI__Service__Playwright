# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Credentials — Temp__File__Manager
#
# Creates a temporary file for the edit session and shreds it on cleanup.
# 1-pass random overwrite before unlink prevents casual recovery.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Temp__File__Manager(Type_Safe):

    suffix: str = '.toml.sg-edit'
    path  : str = ''                                                             # set after create()

    def create(self) -> str:                                                     # returns temp file path
        import tempfile
        fd, p    = tempfile.mkstemp(suffix=self.suffix)
        os.close(fd)
        self.path = p
        return p

    def shred(self, p: str) -> None:                                             # 1-pass overwrite then unlink
        try:
            size = os.path.getsize(p)
            with open(p, 'wb') as f:
                f.write(os.urandom(max(size, 1)))
                f.flush()
                os.fsync(f.fileno())
        except OSError:
            pass
        try:
            os.unlink(p)
        except OSError:
            pass

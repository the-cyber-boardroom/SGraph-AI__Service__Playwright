# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — S3__Vim__Editor
# vim round-trip edit flow for S3 objects.
#
# Protocol (per dev-pack brief §vim integration):
#   1. Download object to temp file; capture ETag.
#   2. Launch $EDITOR (default vim).
#   3. On editor exit 0:
#      a. If file unchanged → skip upload.
#      b. If changed + ETag unchanged → conditional PUT (IfMatch=etag).
#      c. If ETag changed remotely → refuse; write .conflict; exit 1.
#   4. Always clean up temp file unless --keep-local.
#   5. Ctrl-C registered as signal handler to ensure cleanup.
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
import os
import signal
import subprocess
import tempfile

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client import S3__AWS__Client


class S3__Vim__Editor(Type_Safe):
    s3_client  : S3__AWS__Client
    keep_local : bool = False
    editor     : str  = ''                                                        # empty → use $EDITOR → fallback to vim

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.s3_client is None:
            self.s3_client = S3__AWS__Client()

    def edit(self, bucket: str, key: str) -> dict:
        stat = self.s3_client.head_object(bucket, key)
        if stat is None:
            return {'ok': False, 'reason': 'object_not_found'}

        original_etag = stat.etag.unquoted()
        content       = self.s3_client.get_object_body(bucket, key)
        content_type  = stat.content_type or 'application/octet-stream'

        tmpdir   = os.environ.get('SG_AWS__S3__EDIT_TMPDIR', tempfile.gettempdir())
        run_id   = os.urandom(4).hex()
        suffix   = os.path.splitext(key)[-1] or '.txt'
        tmpfile  = os.path.join(tmpdir, f'sg-aws-s3-edit-{run_id}{suffix}')

        original_md5 = hashlib.md5(content).hexdigest()
        cleanup_done = [False]

        def _cleanup(signum=None, frame=None):
            if not cleanup_done[0]:
                cleanup_done[0] = True
                if not self.keep_local and os.path.exists(tmpfile):
                    try:
                        os.unlink(tmpfile)
                    except OSError:
                        pass

        signal.signal(signal.SIGINT,  _cleanup)
        signal.signal(signal.SIGTERM, _cleanup)

        try:
            with open(tmpfile, 'wb') as fh:
                fh.write(content)

            editor = self.editor or os.environ.get('EDITOR', 'vim')
            ret    = subprocess.call([editor, tmpfile])
            if ret != 0:
                return {'ok': False, 'reason': 'editor_error', 'exit_code': ret}

            with open(tmpfile, 'rb') as fh:
                new_content = fh.read()

            new_md5 = hashlib.md5(new_content).hexdigest()
            if new_md5 == original_md5:
                return {'ok': True, 'reason': 'no_change'}

            current_stat  = self.s3_client.head_object(bucket, key)
            current_etag  = current_stat.etag.unquoted() if current_stat else ''

            if current_etag != original_etag:                                     # remote was mutated while editing
                conflict_path = tmpfile + '.conflict'
                with open(conflict_path, 'wb') as fh:
                    fh.write(new_content)
                return {
                    'ok'            : False,
                    'reason'        : 'etag_conflict',
                    'original_etag' : original_etag,
                    'remote_etag'   : current_etag,
                    'conflict_file' : conflict_path,
                }

            uploaded = self.s3_client.put_object(
                bucket         = bucket,
                key            = key,
                body           = new_content,
                content_type   = content_type,
                if_match_etag  = f'"{original_etag}"',
            )
            if not uploaded:
                return {'ok': False, 'reason': 'upload_failed'}
            return {'ok': True, 'reason': 'uploaded'}

        finally:
            _cleanup()

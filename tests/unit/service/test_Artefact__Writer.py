# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Artefact__Writer (sink routing + vault JSON seams)
#
# Integration with real vault/S3 clients is out-of-scope here; the class
# exposes overridable seams, and the tests plug in an in-memory subclass
# (`_InMemoryWriter`) to exercise routing without mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import hashlib
import os
import shutil
import tempfile
from typing                                                                                import Any, Dict, Tuple
from unittest                                                                              import TestCase

import pytest

from sg_compute_specs.playwright.core.schemas.artefact.Schema__Artefact__Ref                   import Schema__Artefact__Ref
from sg_compute_specs.playwright.core.schemas.artefact.Schema__Artefact__Sink_Config           import Schema__Artefact__Sink_Config
from sg_compute_specs.playwright.core.schemas.artefact.Schema__Local_File_Ref                  import Schema__Local_File_Ref
from sg_compute_specs.playwright.core.schemas.artefact.Schema__S3_Ref                          import Schema__S3_Ref
from sg_compute_specs.playwright.core.schemas.artefact.Schema__Vault_Ref                       import Schema__Vault_Ref
from sg_compute_specs.playwright.core.schemas.enums.Enum__Artefact__Sink                       import Enum__Artefact__Sink
from sg_compute_specs.playwright.core.schemas.enums.Enum__Artefact__Type                       import Enum__Artefact__Type
from sg_compute_specs.playwright.core.schemas.primitives.s3.Safe_Str__S3_Bucket                import Safe_Str__S3_Bucket
from sg_compute_specs.playwright.core.schemas.primitives.s3.Safe_Str__S3_Key                   import Safe_Str__S3_Key
from sg_compute_specs.playwright.core.schemas.primitives.vault.Safe_Str__Vault_Key             import Safe_Str__Vault_Key
from sg_compute_specs.playwright.core.schemas.primitives.vault.Safe_Str__Vault_Path            import Safe_Str__Vault_Path
from sg_compute_specs.playwright.core.service.Artefact__Writer                                  import Artefact__Writer, FILENAME_EXTENSIONS, HASH_LEN


class _InMemoryWriter(Artefact__Writer):                                           # Subclass seam — tests run against in-memory sinks, no mocks
    vault_json_store  : Dict[Tuple[str, str], dict]  = None                        # (vault_key, path) -> JSON dict
    vault_bytes_store : Dict[Tuple[str, str], bytes] = None                        # (vault_key, path) -> raw bytes
    s3_store          : Dict[Tuple[str, str], bytes] = None                        # (bucket, key)     -> raw bytes

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vault_json_store  = {}
        self.vault_bytes_store = {}
        self.s3_store          = {}

    def read_from_vault(self, vault_ref):
        return self.vault_json_store.get((str(vault_ref.vault_key), str(vault_ref.path)))

    def write_to_vault(self, vault_ref, data):
        self.vault_json_store[(str(vault_ref.vault_key), str(vault_ref.path))] = data

    def write_bytes_to_vault(self, vault_ref, artefact_type, data):
        self.vault_bytes_store[(str(vault_ref.vault_key), str(vault_ref.path))] = data
        return Schema__Vault_Ref(vault_key=vault_ref.vault_key, path=vault_ref.path)

    def write_bytes_to_s3(self, bucket, prefix, artefact_type, data):
        filename = self.build_local_filename(artefact_type, data)
        key      = Safe_Str__S3_Key(f'{str(prefix).rstrip("/")}/{filename}')
        self.s3_store[(str(bucket), str(key))] = data
        return Schema__S3_Ref(bucket=bucket, key=key)


VAULT_REF = Schema__Vault_Ref(vault_key=Safe_Str__Vault_Key('test-vault'),
                              path     =Safe_Str__Vault_Path('/artefacts/screenshot.png'))


class test_write_artefact__inline(TestCase):

    def test__returns_base64_ref(self):
        w        = _InMemoryWriter()
        data     = b'fake-png-bytes'
        cfg      = Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.INLINE)
        ref      = w.write_artefact(Enum__Artefact__Type.SCREENSHOT, data, cfg)
        assert isinstance(ref, Schema__Artefact__Ref)
        assert ref.sink          == Enum__Artefact__Sink.INLINE
        assert ref.artefact_type == Enum__Artefact__Type.SCREENSHOT
        assert int(ref.size_bytes) == len(data)
        assert str(ref.inline_b64) == base64.b64encode(data).decode('ascii')
        assert ref.vault_ref is None and ref.s3_ref is None and ref.local_ref is None

    def test__content_hash_is_prefix_of_sha256(self):
        w   = _InMemoryWriter()
        raw = b'hello world'
        ref = w.write_artefact(Enum__Artefact__Type.PAGE_CONTENT, raw,
                               Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.INLINE))
        assert str(ref.content_hash) == hashlib.sha256(raw).hexdigest()[:HASH_LEN]
        assert len(str(ref.content_hash)) == HASH_LEN

    def test__disabled_sink_returns_none(self):                                    # enabled=False short-circuits everything
        w   = _InMemoryWriter()
        ref = w.write_artefact(Enum__Artefact__Type.SCREENSHOT, b'x',
                               Schema__Artefact__Sink_Config(enabled=False, sink=Enum__Artefact__Sink.INLINE))
        assert ref is None


class test_write_artefact__vault(TestCase):

    def test__routes_bytes_to_vault_and_returns_vault_ref(self):
        w   = _InMemoryWriter()
        cfg = Schema__Artefact__Sink_Config(enabled        = True                          ,
                                            sink           = Enum__Artefact__Sink.VAULT    ,
                                            sink_vault_ref = VAULT_REF                     )
        ref = w.write_artefact(Enum__Artefact__Type.SCREENSHOT, b'png-data', cfg)
        assert ref.sink == Enum__Artefact__Sink.VAULT
        assert isinstance(ref.vault_ref, Schema__Vault_Ref)
        assert str(ref.vault_ref.vault_key) == 'test-vault'
        assert w.vault_bytes_store[('test-vault', '/artefacts/screenshot.png')] == b'png-data'
        assert ref.inline_b64 is None and ref.s3_ref is None and ref.local_ref is None

    def test__seam_raises_when_not_overridden(self):                               # Base class has no vault client — NotImplementedError, not silent no-op
        base = Artefact__Writer()
        with pytest.raises(NotImplementedError):
            base.write_bytes_to_vault(VAULT_REF, Enum__Artefact__Type.SCREENSHOT, b'x')


class test_write_artefact__s3(TestCase):

    def test__routes_bytes_to_s3_and_returns_s3_ref(self):
        w   = _InMemoryWriter()
        cfg = Schema__Artefact__Sink_Config(enabled        = True                         ,
                                            sink           = Enum__Artefact__Sink.S3      ,
                                            sink_s3_bucket = Safe_Str__S3_Bucket('sg-artefacts'),
                                            sink_s3_prefix = Safe_Str__S3_Key   ('runs/abc')   )
        ref = w.write_artefact(Enum__Artefact__Type.PDF, b'%PDF-1.7', cfg)
        assert ref.sink == Enum__Artefact__Sink.S3
        assert isinstance(ref.s3_ref, Schema__S3_Ref)
        assert str(ref.s3_ref.bucket) == 'sg-artefacts'
        assert str(ref.s3_ref.key).startswith('runs/abc/pdf_')
        assert str(ref.s3_ref.key).endswith('.pdf')
        assert w.s3_store[('sg-artefacts', str(ref.s3_ref.key))] == b'%PDF-1.7'

    def test__seam_raises_when_not_overridden(self):
        base = Artefact__Writer()
        with pytest.raises(NotImplementedError):
            base.write_bytes_to_s3(Safe_Str__S3_Bucket('sg-test'), Safe_Str__S3_Key('k'),
                                   Enum__Artefact__Type.SCREENSHOT, b'x')


class test_write_artefact__local_file(TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='sgraph-artefact-test-')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test__writes_file_to_disk_and_returns_local_ref(self):
        w       = _InMemoryWriter()
        payload = b'console log lines\n'
        cfg     = Schema__Artefact__Sink_Config(enabled           = True                                 ,
                                                sink              = Enum__Artefact__Sink.LOCAL_FILE      ,
                                                sink_local_folder = self.tmp                             )
        ref = w.write_artefact(Enum__Artefact__Type.CONSOLE_LOG, payload, cfg)
        assert ref.sink == Enum__Artefact__Sink.LOCAL_FILE
        assert isinstance(ref.local_ref, Schema__Local_File_Ref)
        path = str(ref.local_ref.path)
        assert os.path.isfile(path)
        assert open(path, 'rb').read() == payload
        assert path.startswith(self.tmp)
        assert path.endswith('.log')                                               # FILENAME_EXTENSIONS maps CONSOLE_LOG -> log

    def test__creates_folder_if_missing(self):
        w        = _InMemoryWriter()
        nested   = os.path.join(self.tmp, 'subdir', 'deeper')
        assert not os.path.exists(nested)
        cfg = Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.LOCAL_FILE, sink_local_folder=nested)
        w.write_artefact(Enum__Artefact__Type.SCREENSHOT, b'png', cfg)
        assert os.path.isdir(nested)


class test_build_local_filename(TestCase):

    def test__all_artefact_types_have_extension(self):                             # Drift guard — any new Enum__Artefact__Type member must get a filename mapping
        assert set(FILENAME_EXTENSIONS.keys()) == set(Enum__Artefact__Type)

    def test__filename_shape(self):
        w        = _InMemoryWriter()
        name     = w.build_local_filename(Enum__Artefact__Type.SCREENSHOT, b'hello')
        expected = f'screenshot_{hashlib.sha256(b"hello").hexdigest()[:HASH_LEN]}.png'
        assert name == expected


class test_vault_json_helpers(TestCase):

    def test__write_then_read_roundtrip(self):                                     # Credentials__Loader.apply() flow: read_from_vault returns the dict written
        w         = _InMemoryWriter()
        state     = {'cookies': [{'name': 'sid', 'value': 'abc'}]}
        w.write_to_vault(VAULT_REF, state)
        loaded = w.read_from_vault(VAULT_REF)
        assert loaded == state

    def test__read_missing_returns_none(self):
        w = _InMemoryWriter()
        assert w.read_from_vault(VAULT_REF) is None

    def test__seam_raises_on_base_class(self):
        base = Artefact__Writer()
        with pytest.raises(NotImplementedError):
            base.read_from_vault(VAULT_REF)
        with pytest.raises(NotImplementedError):
            base.write_to_vault(VAULT_REF, {'k': 'v'})


class test_capture_helpers(TestCase):                                                   # Typed convenience wrappers used by Step__Executor (Phase 2.9)

    def test__capture_screenshot_pins_artefact_type(self):
        w   = _InMemoryWriter()
        cfg = Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.INLINE)
        ref = w.capture_screenshot(b'\x89PNG', cfg)
        assert ref.artefact_type == Enum__Artefact__Type.SCREENSHOT
        assert ref.sink          == Enum__Artefact__Sink.INLINE
        assert ref.inline_b64    is not None

    def test__capture_page_content_pins_artefact_type(self):
        w   = _InMemoryWriter()
        cfg = Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.INLINE)
        ref = w.capture_page_content(b'<html>hi</html>', cfg)
        assert ref.artefact_type == Enum__Artefact__Type.PAGE_CONTENT
        assert str(ref.inline_b64) == base64.b64encode(b'<html>hi</html>').decode('ascii')

    def test__capture_pdf_pins_artefact_type(self):
        w   = _InMemoryWriter()
        cfg = Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.INLINE)
        ref = w.capture_pdf(b'%PDF-1.4', cfg)
        assert ref.artefact_type == Enum__Artefact__Type.PDF

    def test__capture_returns_none_when_sink_disabled(self):                            # Parity with write_artefact()
        w   = _InMemoryWriter()
        cfg = Schema__Artefact__Sink_Config(enabled=False, sink=Enum__Artefact__Sink.INLINE)
        assert w.capture_screenshot  (b'x', cfg) is None
        assert w.capture_page_content(b'x', cfg) is None
        assert w.capture_pdf         (b'x', cfg) is None

    def test__capture_screenshot_routes_through_local_sink(self):                       # End-to-end through the sink
        tmp  = tempfile.mkdtemp()
        try:
            w   = _InMemoryWriter()
            cfg = Schema__Artefact__Sink_Config(enabled=True, sink=Enum__Artefact__Sink.LOCAL_FILE, sink_local_folder=tmp)
            ref = w.capture_screenshot(b'\x89PNG\r\n\x1a\n', cfg)
            assert ref.sink          == Enum__Artefact__Sink.LOCAL_FILE
            assert ref.artefact_type == Enum__Artefact__Type.SCREENSHOT
            assert ref.local_ref is not None and os.path.exists(str(ref.local_ref.path))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

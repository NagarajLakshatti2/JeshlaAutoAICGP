"""Capture metadata is local byte evidence, never a worker-supplied claim."""
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agent.tools.project_tools import ProjectTools
from integrations.web import inspection


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j/WQAAAAASUVORK5CYII=')


class InspectionDownloadMetadataTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.tools = ProjectTools(str(self.root))

    def capture(self, raw=PNG, reply=None):
        worker = Mock()
        worker.returncode = 0
        worker.poll.return_value = 0
        def communicate(payload, timeout):
            if raw is not None:
                Path(json.loads(payload)['screenshot']).write_bytes(raw)
            return json.dumps(reply or {'status': 'inspected', 'fields': [], 'buttons': []}), ''
        worker.communicate.side_effect = communicate
        with patch.object(inspection.subprocess, 'Popen', return_value=worker):
            return self.tools.inspect_browser_page('https://example.test')

    def local_png(self):
        folder = self.root / 'capture'
        folder.mkdir()
        (folder / 'inspection.png').write_bytes(PNG)
        return folder

    def assert_no_metadata(self, result):
        self.assertNotIn('screenshot_sha256', result)
        self.assertNotIn('screenshot_size_bytes', result)

    def test_exact_png_metadata_is_saved_before_inspection_digest(self):
        result = self.capture()
        self.assertEqual(result['screenshot_sha256'], hashlib.sha256(PNG).hexdigest())
        self.assertEqual(result['screenshot_size_bytes'], len(PNG))
        raw = (self.root / result['inspection_file']).read_bytes()
        saved = json.loads(raw)
        self.assertEqual(saved['screenshot_sha256'], result['screenshot_sha256'])
        self.assertEqual(saved['screenshot_size_bytes'], len(PNG))
        self.assertNotIn('inspection_sha256', saved)
        self.assertEqual(result['inspection_sha256'], hashlib.sha256(raw).hexdigest())

    def test_missing_empty_or_non_png_preserves_inspection_without_metadata(self):
        for raw in (None, b'', b'not a PNG'):
            with self.subTest(raw=raw):
                result = self.capture(raw)
                self.assertEqual(result['status'], 'inspected')
                self.assert_no_metadata(result)
                self.assert_no_metadata(json.loads((self.root / result['inspection_file']).read_bytes()))

    def test_worker_metadata_and_path_cannot_claim_a_missing_capture(self):
        result = self.capture(None, {'status': 'inspected', 'fields': [],
            'screenshot': '../other.png', 'screenshot_sha256': 'a' * 64, 'screenshot_size_bytes': 1})
        self.assert_no_metadata(result)
        self.assertEqual(Path(result['screenshot']).name, 'inspection.png')
        self.assertEqual(Path(result['screenshot']).parent, Path(result['inspection_file']).parent)

    def test_oversized_capture_is_ineligible(self):
        with patch.object(inspection, 'MAX_SCREENSHOT_BYTES', len(PNG) - 1):
            self.assert_no_metadata(self.capture())

    def test_symlink_or_junction_capture_path_is_ineligible(self):
        folder = self.local_png()
        for method in ('is_symlink', 'is_junction'):
            with self.subTest(method=method), patch.object(Path, method, return_value=True, create=True):
                self.assertEqual(inspection._screenshot_metadata(self.root, folder), {})

    def test_capture_changed_during_read_is_ineligible(self):
        folder = self.local_png()
        original = os.fstat
        calls = 0
        def changed_stat(descriptor):
            nonlocal calls
            calls += 1
            stat = original(descriptor)
            return SimpleNamespace(st_dev=stat.st_dev, st_ino=stat.st_ino, st_size=stat.st_size,
                st_mtime_ns=stat.st_mtime_ns + (1 if calls == 2 else 0), st_ctime_ns=stat.st_ctime_ns)
        with patch.object(inspection.os, 'fstat', side_effect=changed_stat):
            self.assertEqual(inspection._screenshot_metadata(self.root, folder), {})

    def test_capture_read_failure_does_not_fail_completed_inspection(self):
        folder = self.local_png()
        with patch.object(Path, 'open', side_effect=PermissionError('fixture')):
            self.assertEqual(inspection._screenshot_metadata(self.root, folder), {})


if __name__ == '__main__':
    unittest.main()

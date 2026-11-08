import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / '.agents/skills/work-sync/scripts/sync.py'
spec = importlib.util.spec_from_file_location('sync', SCRIPT)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], stderr=subprocess.DEVNULL).decode().strip()

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'project'
        self.repo.mkdir()
        git(self.repo, 'init')
        self.remote = self.base / 'remote.git'
        self.remote.mkdir()
        git(self.remote, 'init', '--bare')
        self.state = self.base / 'queue'
        (self.repo / 'main.py').write_text('print("hello")\n')

    def tearDown(self):
        self.tmp.cleanup()

    def run_sync(self, repo=None, state=None):
        args = type('Args', (), {'repo': str(repo or self.repo), 'state': str(state or self.state), 'remote': str(self.remote)})()
        with patch.object(sync.time, 'sleep'):
            sync.sync(args)

    def manifests(self):
        paths = git(self.remote, 'ls-tree', '-r', '--name-only', 'agent-handoff').splitlines()
        return [(p, json.loads(git(self.remote, 'show', 'agent-handoff:' + p))) for p in paths if p.endswith('manifest.json')]

    def test_remote_recovery_and_noop(self):
        self.run_sync()
        first = git(self.remote, 'rev-parse', 'agent-handoff')
        self.run_sync()
        self.assertEqual(first, git(self.remote, 'rev-parse', 'agent-handoff'))
        for path, manifest in self.manifests():
            for name, expected in manifest['files'].items():
                data = subprocess.check_output(['git','-C',str(self.remote),'show','agent-handoff:' + str(Path(path).parent / 'files' / name)])
                self.assertEqual(expected, hashlib.sha256(data).hexdigest())
        self.assertEqual(git(self.repo, 'diff', '--cached', '--name-only'), '')

    def test_secret_binary_symlink_and_ignored_excluded(self):
        (self.repo / '.env').write_text('SENSITIVE=private')
        (self.repo / 'token.txt').write_text('ghp_' + 'a' * 32)
        (self.repo / 'image.bin').write_bytes(b'\x00\xff')
        (self.repo / 'big.txt').write_bytes(b'x' * (sync.MAX_BYTES + 1))
        (self.repo / 'outside').symlink_to('/etc/passwd')
        (self.repo / '.gitignore').write_text('ignored.txt\n')
        (self.repo / 'ignored.txt').write_text('private')
        self.run_sync()
        m = self.manifests()[0][1]
        self.assertEqual(set(m['files']), {'main.py', '.gitignore'})
        self.assertEqual(len(m['omitted']), 5)

    def test_outage_queues_and_retries(self):
        offline = self.base / 'offline.git'
        self.remote.rename(offline)
        with self.assertRaises(RuntimeError):
            self.run_sync()
        self.assertEqual(json.loads((self.state / 'status.json').read_text())['state'], 'pending')
        self.assertTrue((self.state / 'store/.git').is_dir())
        (self.repo / 'main.py').write_text('print("recovered")\n')
        offline.rename(self.remote)
        self.run_sync()
        self.assertEqual(len(self.manifests()), 2)
        self.assertEqual(json.loads((self.state / 'status.json').read_text())['state'], 'verified')

    def test_independent_sessions_and_divergence_preserved(self):
        self.run_sync()
        other = self.base / 'other'
        other.mkdir()
        git(other, 'init')
        (other / 'other.txt').write_text('second machine')
        self.run_sync(other, self.base / 'other-state')
        (self.repo / 'main.py').write_text('first machine continued')
        self.run_sync()
        self.assertEqual(len(self.manifests()), 3)
        self.assertEqual(len({m['session'] for _, m in self.manifests()}), 2)

    def test_deletion_reflected_in_new_snapshot(self):
        self.run_sync()
        (self.repo / 'main.py').unlink()
        self.run_sync()
        manifests = sorted((m for _, m in self.manifests()), key=lambda m: m['captured_at'])
        self.assertIn('main.py', manifests[0]['files'])
        self.assertNotIn('main.py', manifests[1]['files'])

    def test_state_inside_source_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'outside project'):
            self.run_sync(state=self.repo / 'bad-state')

if __name__ == '__main__':
    unittest.main()

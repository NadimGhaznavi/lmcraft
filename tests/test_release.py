"""Verify the BMForge release workflow against disposable local Git remotes."""

import ast
import os
from pathlib import Path
import pty
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONSTANTS = 'lmcraft/constants/DLMCraft.py'


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='lmcraft-release-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.environment = {
            **os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
            'GIT_TERMINAL_PROMPT': '0', 'GIT_AUTHOR_NAME': 'Release Test',
            'GIT_AUTHOR_EMAIL': 'test@example.invalid', 'GIT_COMMITTER_NAME': 'Release Test',
            'GIT_COMMITTER_EMAIL': 'test@example.invalid', 'PYTHONDONTWRITEBYTECODE': '1',
            'NO_COLOR': '1', 'TERM': 'dumb', 'TZ': 'America/Toronto',
        }
        self.git('init', '-b', 'main')
        self.git('init', '--bare', str(self.root / 'remote.git'))
        self.git('remote', 'add', 'origin', str(self.root / 'remote.git'))
        for name in ('scripts/new-release.sh', 'scripts/check-cmdb.py', 'scripts/install.sh',
                     'scripts/upgrade.sh', 'scripts/uninstall.sh', CONSTANTS, 'CHANGELOG.md'):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        self.commit('Initial project')
        self.git('branch', 'dev')
        self.git('push', 'origin', 'main', 'dev')
        self.git('switch', '-c', 'feat/maint-0.1.0')
        (self.repo / 'feature.txt').write_text('Feature ready for release\n')
        self.commit('Add feature')

    def command(self, *arguments, check=True):
        return subprocess.run(arguments, cwd=self.repo, env=self.environment,
                              capture_output=True, text=True, check=check, timeout=30)

    def git(self, *arguments):
        return self.command('git', *arguments).stdout.strip()

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)

    def release(self, *arguments, answer='y', terminal=True):
        command = ['bash', 'scripts/new-release.sh', *arguments]
        if not terminal:
            return self.command(*command, check=False)
        master, slave = pty.openpty()
        try:
            with subprocess.Popen(command, cwd=self.repo, env=self.environment, stdin=slave,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
                os.close(slave)
                slave = None
                os.write(master, (answer + '\n').encode())
                try:
                    output, errors = process.communicate(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    raise
                return subprocess.CompletedProcess(command, process.returncode, output, errors)
        finally:
            os.close(master)
            if slave is not None:
                os.close(slave)

    def assert_rejected(self, arguments, error, **options):
        refs = self.git('show-ref')
        branch = self.git('branch', '--show-current')
        metadata = (self.repo / CONSTANTS).read_bytes()
        result = self.release(*arguments, **options)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(error, result.stderr, result.stdout)
        self.assertEqual(self.git('show-ref'), refs)
        self.assertEqual(self.git('branch', '--show-current'), branch)
        self.assertEqual((self.repo / CONSTANTS).read_bytes(), metadata)

    def test_release_updates_metadata_tag_and_local_remote_branches(self):
        codename = 'First world "ready" — café'
        result = self.release('0.1.0', codename)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git('branch', '--show-current'), 'feat/maint-0.1.1')
        tip = self.git('rev-parse', 'HEAD')
        for ref in ('main', 'dev', 'origin/main', 'origin/dev', 'v0.1.0^{commit}'):
            self.assertEqual(self.git('rev-parse', ref), tip)
        self.assertEqual(self.git('cat-file', '-t', 'v0.1.0'), 'tag')
        tree = ast.parse((self.repo / CONSTANTS).read_text())
        values = {node.target.id: ast.literal_eval(node.value) for node in ast.walk(tree)
                  if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)}
        self.assertEqual(values['VERSION'], '0.1.0')
        self.assertEqual(values['CMDB_CODENAME'], codename)
        changelog = (self.repo / 'CHANGELOG.md').read_text()
        self.assertEqual(changelog.count('## [Unreleased]'), 1)
        self.assertIn('## [0.1.0] - ', changelog)
        self.assertIn('### Summary', changelog)
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertNotIn('refs/heads/feat/maint-0.1.1', self.git('ls-remote', 'origin'))

    def test_cancel_and_noninteractive_execution_preserve_release_state(self):
        refs = self.git('show-ref')
        result = self.release('0.1.0', 'Cancelled', answer='n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('cancelled', result.stdout)
        self.assertEqual(self.git('show-ref'), refs)
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assert_rejected(('0.1.0', 'Unattended'), 'interactive terminal', terminal=False)

    def test_invalid_version_and_dirty_tree_fail_before_release(self):
        self.assert_rejected(('v0.1.0', 'Invalid'), 'Use a version')
        (self.repo / 'pending.txt').write_text('Uncommitted\n')
        self.assert_rejected(('0.1.0', 'Dirty'), 'Commit or stash')

    def test_missing_lifecycle_entry_point_is_rejected(self):
        (self.repo / 'scripts/upgrade.sh').chmod(0o644)
        self.commit('Break upgrade permissions')
        self.assert_rejected(('0.1.0', 'Incomplete'), 'Missing executable scripts/upgrade.sh')

    def test_tag_collision_and_inconsistent_branch_ancestry_are_rejected(self):
        self.git('tag', 'v0.1.0')
        self.assert_rejected(('0.1.0', 'Duplicate'), 'Tag v0.1.0 already exists')
        self.git('tag', '-d', 'v0.1.0')
        self.git('switch', 'main')
        (self.repo / 'main-change.txt').write_text('Main advanced\n')
        self.commit('Advance main')
        self.git('switch', 'feat/maint-0.1.0')
        self.assert_rejected(('0.1.0', 'Outdated'), 'Merge main into dev')

    def test_rejected_atomic_push_leaves_remote_refs_unchanged(self):
        before = self.git('ls-remote', 'origin')
        hook = self.root / 'remote.git/hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        result = self.release('0.1.0', 'Rejected remotely')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git('ls-remote', 'origin'), before)
        self.assertEqual(self.git('cat-file', '-t', 'v0.1.0'), 'tag')


if __name__ == '__main__':
    unittest.main()

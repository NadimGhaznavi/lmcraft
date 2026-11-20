"""Exercise managed files with the real MOO binary and a disposable service fixture."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('deployment', ROOT / 'scripts/install.py')
deployment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deployment)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='lmcraft-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'checkout'
        for name in (*deployment.COPY_FILES, 'scripts/check-cmdb.py',
                     'lmcraft/constants/DLMCraft.py', deployment.CORE_FILE):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        self.destination = self.root / 'installed'
        self.installation = deployment.Installation(self.source, destination=self.destination, run=self.run_fixture)
        self.installation.metadata['BASE_DIR'] = str(self.destination)
        self.installation.service_unit = self.root / 'systemd/lmcraft.service'
        self.chown = patch.object(deployment.shutil, 'chown')
        self.chown.start()
        self.addCleanup(self.chown.stop)
        self.calls = []

    def run_fixture(self, arguments, **kwargs):
        self.calls.append(arguments)
        if arguments[0].endswith('/bin/moo'):
            return subprocess.run(arguments, **kwargs)
        output = ''
        if arguments[0] == 'getent':
            output = f'lmcraft:x:999:999::{self.destination}:/usr/sbin/nologin\n'
        elif arguments[0].endswith('/check-health'):
            output = 'LMCraft is accepting MOO connections\n'
        return subprocess.CompletedProcess(arguments, 0, output, '')

    def test_install_upgrade_remove_and_reinstall_preserve_world(self):
        self.installation.apply('install')
        database = self.destination / 'data/lmcraft.db'
        world = database.read_bytes()
        credentials = self.destination / 'conf/bootstrap-credentials'
        secret = credentials.read_bytes()
        self.assertEqual(credentials.stat().st_mode & 0o777, 0o600)
        self.assertTrue(self.installation.service_unit.is_file())
        self.assertEqual((self.destination / deployment.VERSION_MARKER).read_text(), '0.0.0\n')
        self.installation.apply('install')
        config = self.destination / deployment.NETWORK_CONFIG
        config.write_text('MOO_BIND_IP=127.0.0.1\nMOO_PORT=13333\n')
        self.installation.metadata['VERSION'] = '0.0.1'
        self.installation.apply('upgrade')
        self.assertEqual((self.destination / deployment.VERSION_MARKER).read_text(), '0.0.1\n')
        self.assertIn('13333', config.read_text())
        self.assertEqual(database.read_bytes(), world)
        self.assertEqual(credentials.read_bytes(), secret)
        self.installation.apply('uninstall')
        self.installation.apply('uninstall')
        self.assertFalse(self.installation.service_unit.exists())
        self.assertFalse((self.destination / 'bin/moo').exists())
        self.assertFalse((self.destination / deployment.VERSION_MARKER).exists())
        self.assertEqual(database.read_bytes(), world)
        self.assertEqual(credentials.read_bytes(), secret)
        self.assertTrue(json.loads((self.destination / deployment.MANIFEST).read_text())['removed'])
        self.installation.apply('install')
        self.assertEqual(database.read_bytes(), world)

    def test_check_is_read_only_and_prerequisites_match_real_operation(self):
        self.installation.apply('install', check=True)
        self.assertFalse(self.destination.exists())
        with patch.object(deployment.shutil, 'which', side_effect=lambda name: None if name == 'timeout' else '/bin/' + name):
            for check in (True, False):
                with self.assertRaisesRegex(ValueError, 'timeout'):
                    self.installation.apply('install', check=check)
                self.assertFalse(self.destination.exists())

    def test_failed_activation_keeps_successful_marker(self):
        self.installation.apply('install')
        self.installation.metadata['VERSION'] = '0.0.1'
        with patch.object(deployment, 'HEALTH_TIMEOUT', 0):
            with self.assertRaisesRegex(ValueError, 'welcome banner'):
                self.installation.apply('upgrade')
        self.assertEqual((self.destination / deployment.VERSION_MARKER).read_text(), '0.0.0\n')

    def test_invalid_config_and_unowned_unit_fail_before_changes(self):
        self.installation.service_unit.parent.mkdir()
        self.installation.service_unit.write_text('unrelated service')
        with self.assertRaisesRegex(ValueError, 'unowned unit'):
            self.installation.apply('install')
        self.assertFalse(self.destination.exists())
        self.installation.service_unit.unlink()
        self.installation.apply('install')
        (self.destination / deployment.NETWORK_CONFIG).write_text('MOO_PORT=not-a-port\n')
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, 'MOO_PORT'):
            self.installation.apply('upgrade')
        self.assertNotIn(['systemctl', 'stop', deployment.SERVICE_NAME], self.calls)


if __name__ == '__main__':
    unittest.main()

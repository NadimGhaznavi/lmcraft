"""Exercise managed files with the real MOO binary and a disposable service fixture."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('deployment', ROOT / 'scripts/install.py')
deployment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deployment)


class InstallationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Compile once from repository inputs, with no prebuilt executable or downloads.
        cls.build_temporary = tempfile.TemporaryDirectory(prefix='lmcraft-build-test-')
        cls.addClassCleanup(cls.build_temporary.cleanup)
        cls.built_checkout = Path(cls.build_temporary.name) / 'checkout'
        for directory in (deployment.SOURCE_DIR, 'deploy', 'lmcraft', 'scripts'):
            shutil.copytree(ROOT / directory, cls.built_checkout / directory)
        instance = deployment.Installation(cls.built_checkout, destination=Path(cls.build_temporary.name) / 'unused')
        instance.validate_build_inputs()
        instance.prepare_build()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='lmcraft-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'checkout'
        for name in (*deployment.COPY_FILES, 'scripts/check-cmdb.py',
                     'lmcraft/constants/DLMCraft.py', deployment.CORE_FILE, deployment.SOURCE_MANIFEST):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.built_checkout / name, target)
        shutil.copytree(self.built_checkout / deployment.SOURCE_DIR, self.source / deployment.SOURCE_DIR)
        self.destination = self.root / 'installed'
        self.installation = deployment.Installation(self.source, destination=self.destination, run=self.run_fixture)
        self.installation.metadata['BASE_DIR'] = str(self.destination)
        self.installation.service_unit = self.root / 'systemd/lmcraft.service'
        self.chown = patch.object(deployment.shutil, 'chown')
        self.chown.start()
        self.addCleanup(self.chown.stop)
        self.calls = []
        self.packages_missing = False
        self.build = patch.object(self.installation, 'prepare_build', side_effect=self.stage_built_binary)
        self.build_mock = self.build.start()
        self.addCleanup(self.build.stop)

    def stage_built_binary(self):
        target = self.source / deployment.GENERATED_BINARY
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(self.built_checkout / deployment.GENERATED_BINARY, target)

    def run_fixture(self, arguments, **kwargs):
        self.calls.append(arguments)
        if Path(arguments[0]).name == 'moo' or arguments[0] in ('/bin/sh', 'make'):
            return subprocess.run(arguments, **kwargs)
        output = ''
        if arguments[0] == 'getent':
            output = f'lmcraft:x:999:999::{self.destination}:/usr/sbin/nologin\n'
        elif arguments[0] == 'dpkg-query':
            output = ''.join(f'{name}\tinstalled\n' for name in deployment.REQUIRED_PACKAGES
                             if not self.packages_missing or name != 'gperf')
        elif arguments[:2] == ['apt-get', 'install']:
            self.packages_missing = False
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

    def test_fresh_checkout_builds_and_seeds_a_new_world(self):
        (self.source / deployment.GENERATED_BINARY).unlink()
        self.build.stop()
        self.installation.apply('install')
        self.assertTrue((self.destination / 'data/lmcraft.db').is_file())
        self.assertNotEqual((self.destination / 'data/lmcraft.db').read_bytes(),
                            (self.source / deployment.CORE_FILE).read_bytes())
        self.assertFalse((self.source / 'downloads').exists())
        self.assertFalse(any('curl' in str(call) or 'wget' in str(call) for call in self.calls))
        self.installation.validate_build_inputs()
        # The installed runtime must work with its development checkout unavailable.
        self.source.rename(self.source.with_name('checkout-hidden'))
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        process = subprocess.Popen([str(self.destination / 'scripts/run-moo')], cwd=self.destination,
                                   env={**os.environ, 'MOO_BIND_IP': '127.0.0.1', 'MOO_PORT': str(port)},
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    connection = socket.create_connection(('127.0.0.1', port), timeout=1)
                    break
                except ConnectionRefusedError:
                    if time.monotonic() >= deadline or process.poll() is not None:
                        raise
                    time.sleep(0.1)
            with connection:
                connection.settimeout(2)
                received = b''
                while b'Welcome' not in received:
                    chunk = connection.recv(65536)
                    self.assertTrue(chunk)
                    received += chunk
                password = (self.destination / 'conf/bootstrap-credentials').read_text().splitlines()[1].removeprefix('Password: ')
                connection.sendall(('connect Wizard ' + password + '\r\n;server_version()\r\n').encode())
                received = b''
                while b'1.9.0alpha' not in received:
                    chunk = connection.recv(65536)
                    self.assertTrue(chunk)
                    received += chunk
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

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

    def test_missing_packages_check_never_installs_or_builds(self):
        self.packages_missing = True
        with self.assertRaisesRegex(ValueError, 'gperf'):
            self.installation.apply('install', check=True)
        self.assertFalse(self.destination.exists())
        self.build_mock.assert_not_called()
        self.assertFalse(any(call[0] == 'apt-get' for call in self.calls))

    def test_package_install_failure_keeps_existing_service_and_version(self):
        self.installation.apply('install')
        self.calls.clear()
        self.packages_missing = True
        original_run = self.installation.run
        def fail_apt(arguments, **kwargs):
            if arguments[0] == 'apt-get':
                raise subprocess.CalledProcessError(100, arguments)
            return original_run(arguments, **kwargs)
        self.installation.run = fail_apt
        self.build.stop()
        with self.assertRaises(subprocess.CalledProcessError):
            self.installation.apply('upgrade')
        self.assertNotIn(['systemctl', 'stop', deployment.SERVICE_NAME], self.calls)
        self.assertEqual((self.destination / deployment.VERSION_MARKER).read_text(), '0.0.0\n')

    def test_build_failure_keeps_existing_service_and_version(self):
        self.installation.apply('install')
        self.calls.clear()
        self.build.stop()
        with patch.object(self.installation, 'missing_packages', return_value=[]), \
                patch.object(deployment, 'command', side_effect=subprocess.CalledProcessError(2, ['make'])):
            with self.assertRaises(subprocess.CalledProcessError):
                self.installation.apply('upgrade')
        self.assertNotIn(['systemctl', 'stop', deployment.SERVICE_NAME], self.calls)
        self.assertEqual((self.destination / deployment.VERSION_MARKER).read_text(), '0.0.0\n')

    def test_modified_source_or_seed_rejected_before_provisioning(self):
        seed = self.source / deployment.CORE_FILE
        seed.write_text('untrusted seed')
        with self.assertRaisesRegex(ValueError, 'LambdaCore'):
            self.installation.apply('install')
        self.build_mock.assert_not_called()
        self.assertFalse(self.destination.exists())

    def test_modified_upstream_source_rejected_before_provisioning(self):
        source = self.source / deployment.SOURCE_DIR / 'server.c'
        source.chmod(0o644)
        source.write_text('changed upstream source')
        with self.assertRaisesRegex(ValueError, 'source is missing or changed'):
            self.installation.apply('install')
        self.build_mock.assert_not_called()
        self.assertFalse(self.destination.exists())

    def test_uninstall_does_not_need_build_inputs_or_tools(self):
        self.installation.apply('install')
        for directory in (self.source / deployment.SOURCE_DIR).rglob('*'):
            if directory.is_dir():
                directory.chmod(0o755)
        (self.source / deployment.SOURCE_DIR).chmod(0o755)
        shutil.rmtree(self.source / deployment.SOURCE_DIR)
        (self.source / deployment.CORE_FILE).unlink()
        with patch.object(self.installation, 'missing_packages', side_effect=AssertionError('Build packages checked on uninstall')):
            self.installation.apply('uninstall')
        self.assertFalse((self.destination / deployment.VERSION_MARKER).exists())

    def test_missing_packages_are_installed_before_build(self):
        self.packages_missing = True
        self.build.stop()
        real_command = deployment.command
        def controlled_command(arguments, **kwargs):
            if arguments[0] == 'make':
                shutil.copy2(self.built_checkout / deployment.GENERATED_BINARY, Path(kwargs['cwd']) / 'moo')
                return subprocess.CompletedProcess(arguments, 0)
            if arguments[0] == '/bin/sh':
                self.assertFalse(self.packages_missing, 'configure ran before package installation')
                return subprocess.CompletedProcess(arguments, 0)
            return real_command(arguments, **kwargs)
        with patch.object(deployment, 'command', side_effect=controlled_command):
            self.installation.apply('install')
        self.assertIn(['apt-get', 'update'], self.calls)
        self.assertIn(['apt-get', 'install', '-y', '--no-install-recommends', 'gperf'], self.calls)


if __name__ == '__main__':
    unittest.main()

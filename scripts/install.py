#!/usr/bin/env python3
"""Install, upgrade or uninstall LMCraft's native LambdaMOO service."""

import argparse
import importlib.util
import json
import hashlib
from ipaddress import IPv4Address
import secrets
import time
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile


BMFORGE_COMPONENT = {"id": "bmforge.installation", "spec_version": "0.1.3"}

PROJECT_NAME = "LMCraft"
# Turn this on only after implementing the project's full deployment contract.
DEPLOYMENT_READY = True
COPY_TREES = ("lmcraft",)
COPY_FILES = ("bin/moo", "scripts/run-moo", "scripts/check-health", "deploy/lmcraft.service")
# Set to "requirements.txt" for Python applications requiring a production venv.
# Keep None for applications without Python package dependencies.
REQUIREMENTS_FILE = None
VENV_DIR = ".venv"
# Use the host interpreter, never an activated development checkout venv.
SYSTEM_PYTHON = "/usr/bin/python3"
# Adapt to the deployed application's service/client imports when enabling deployment.
RUNTIME_IMPORTS = ()
MANIFEST = ".installation-manifest.json"
VERSION_MARKER = ".deployment-version"
SERVICE_NAME = "lmcraft.service"
SERVICE_USER = "lmcraft"
SERVICE_UNIT = Path("/etc/systemd/system/lmcraft.service")
NETWORK_CONFIG = "conf/lmcraft.env"
DEFAULT_NETWORK = {"MOO_BIND_IP": "0.0.0.0", "MOO_PORT": "3333"}
CORE_FILE = "deploy/LambdaCore-17May04.db"
CORE_SHA256 = "e453a0d4f837db9969e2fa00250c3a58aafcf0d843d96495c1dd81924ebf4747"
HEALTH_TIMEOUT = 30
SOURCE_DIR = "MOO-1.9.0alpha"
SOURCE_MANIFEST = "deploy/moo-source.sha256"
GENERATED_BINARY = "bin/moo"
REQUIRED_PACKAGES = ("build-essential", "bison", "gperf", "libcrypt-dev")
BUILD_ARGUMENTS = ("--enable-sz=i32,bq32",)
BUILD_JOBS = 2
BUILD_TIMEOUT = 600
PACKAGE_TIMEOUT = 600


def command(arguments: list[str], *, run=subprocess.run, **kwargs):
    """Show provisioning/build commands without logging private bootstrap input."""
    print('+', *arguments, flush=True)
    return run(arguments, check=True, **kwargs)


def relative_path(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("Managed paths must be strings")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or '..' in path.parts or path.as_posix() != name or name == '.':
        raise ValueError(f"Invalid managed path: {name}")
    if name in (MANIFEST, VERSION_MARKER):
        raise ValueError(f"Reserved bookkeeping path: {name}")
    return name


def reject_symlinks(path: Path) -> None:
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError(f"Refusing a symbolic link in deployment path: {candidate}")


class Installation:
    def __init__(self, checkout: Path, *, destination: Path | None = None,
                 run=None) -> None:
        self.checkout = checkout.resolve()
        self.run = run or subprocess.run
        self.version_file = f"{PROJECT_NAME.lower()}/constants/D{PROJECT_NAME}.py"
        spec = importlib.util.spec_from_file_location('cmdb_checker', self.checkout / 'scripts/check-cmdb.py')
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        self.metadata = checker.validate((self.checkout / self.version_file).read_text(),
                                         PROJECT_NAME, self.version_file)
        self.destination = Path(destination if destination is not None else self.metadata['BASE_DIR']).absolute()
        self.service_unit = SERVICE_UNIT
        reject_symlinks(self.destination)
        if (self.checkout.is_relative_to(self.destination)
                or self.destination.is_relative_to(self.checkout)):
            raise ValueError("Run deployment from a separate checkout outside the installation")

    def validate_build_inputs(self) -> None:
        manifest = self.checkout / SOURCE_MANIFEST
        reject_symlinks(manifest)
        if not manifest.is_file():
            raise ValueError(f"Missing bundled source manifest: {SOURCE_MANIFEST}")
        for line in manifest.read_text().splitlines():
            digest, separator, name = line.partition('  ')
            if not separator or len(digest) != 64 or not name.startswith(SOURCE_DIR + '/'):
                raise ValueError("Invalid bundled source checksum manifest")
            source = self.checkout / relative_path(name)
            reject_symlinks(source)
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
                raise ValueError(f"Bundled LambdaMOO source is missing or changed: {name}")
        if not (self.checkout / SOURCE_DIR / 'configure').is_file():
            raise ValueError("The bundled source must include configure")
        if (self.checkout / SOURCE_DIR / 'config.status').exists():
            raise ValueError("Bundled source contains an in-source build; restore the pristine source")
        core = self.checkout / CORE_FILE
        reject_symlinks(core)
        if not core.is_file() or hashlib.sha256(core.read_bytes()).hexdigest() != CORE_SHA256:
            raise ValueError(f"Bundled LambdaCore seed is missing or changed: {CORE_FILE}")
        for name in ('build', 'bin', GENERATED_BINARY):
            reject_symlinks(self.checkout / name)

    def missing_packages(self) -> list[str]:
        os_release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
        if os_release.get('ID', '').strip('"') not in ('debian', 'ubuntu'):
            raise ValueError("Automatic installation supports Debian/Ubuntu systemd hosts")
        for executable in ('apt-get', 'dpkg-query'):
            if shutil.which(executable) is None:
                raise ValueError(f"Missing required executable: {executable}")
        result = self.run(['dpkg-query', '-W', '-f=${Package}\t${db:Status-Status}\n', *REQUIRED_PACKAGES],
                          capture_output=True, text=True)
        if result.returncode not in (0, 1):
            raise ValueError("Unable to inspect build prerequisites with dpkg-query")
        installed = dict(line.split('\t', 1) for line in result.stdout.splitlines() if '\t' in line)
        return [name for name in REQUIRED_PACKAGES if installed.get(name) != 'installed']

    def prepare_build(self) -> None:
        missing = self.missing_packages()
        if missing:
            command(['apt-get', 'update'], run=self.run, timeout=PACKAGE_TIMEOUT)
            command(['apt-get', 'install', '-y', '--no-install-recommends', *missing],
                    run=self.run, timeout=PACKAGE_TIMEOUT,
                    env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
            if self.missing_packages():
                raise ValueError("Build prerequisites are still missing after apt-get installation")
        for executable in ('gcc', 'make', 'bison', 'gperf'):
            if shutil.which(executable) is None:
                raise ValueError(f"Required build tool is missing after package setup: {executable}")
        build_root = self.checkout / 'build'
        build_root.mkdir(exist_ok=True)
        # A new VPATH directory on every run prevents reuse of a stale executable.
        with tempfile.TemporaryDirectory(prefix='moo-', dir=build_root) as folder:
            build = Path(folder)
            source = self.checkout / SOURCE_DIR
            print(f'Build directory: {build}', flush=True)
            command(['/bin/sh', str(source / 'configure'), f'--srcdir={source}', *BUILD_ARGUMENTS],
                    run=self.run, cwd=build, timeout=BUILD_TIMEOUT)
            command(['make', f'-j{BUILD_JOBS}'], run=self.run, cwd=build, timeout=BUILD_TIMEOUT)
            result = self.run([str(build / 'moo'), '-e', str(source / 'Minimal.db'), '/dev/null',
                               '-a', '127.0.0.1', '0'],
                              input=';{server_version(), 2147483647 + 1}\nabort\n',
                              capture_output=True, text=True, timeout=60)
            if (result.returncode != 1 or '"1.9.0alpha"' not in result.stdout
                    or '-2147483648' not in result.stdout):
                raise ValueError("Compiled server failed its offline version/arithmetic smoke test")
            self.atomic_write(self.checkout / GENERATED_BINARY, (build / 'moo').read_bytes(), 0o755)

    def network(self) -> dict[str, str]:
        values = DEFAULT_NETWORK.copy()
        path = self.destination / NETWORK_CONFIG
        reject_symlinks(path)
        if path.exists():
            for line in path.read_text().splitlines():
                if not line.strip() or line.lstrip().startswith('#'):
                    continue
                key, separator, value = line.partition('=')
                if not separator or key not in values:
                    raise ValueError(f"Invalid network setting in {path}: {key}")
                values[key] = value
        IPv4Address(values['MOO_BIND_IP'])
        if not values['MOO_PORT'].isascii() or not values['MOO_PORT'].isdigit() or not 1024 <= int(values['MOO_PORT']) <= 65535:
            raise ValueError("MOO_PORT must be an unprivileged TCP port (1024–65535)")
        return values

    def preflight_service(self, action: str, previous: list[str] | None) -> None:
        if self.destination != Path(self.metadata['BASE_DIR']):
            raise ValueError("The service must be installed at its declared BASE_DIR")
        executables = ['systemctl']
        if action != 'uninstall':
            executables += ['getent', 'systemd-analyze', 'bash', 'timeout', 'cp', 'mv']
        for executable in executables:
            if shutil.which(executable) is None:
                raise ValueError(f"Missing required executable: {executable}")
        self.run(['systemctl', 'show', '--property=Version'], check=True, capture_output=True, text=True)
        reject_symlinks(self.service_unit)
        if self.service_unit.exists():
            manifest = self.destination / MANIFEST
            owned = manifest.is_file() and json.loads(manifest.read_text()).get('service_unit') == str(self.service_unit)
            if not owned:
                raise ValueError(f"Refusing to replace an unowned unit: {self.service_unit}")
            installed_unit = self.destination / 'deploy/lmcraft.service'
            if not installed_unit.is_file() or installed_unit.read_bytes() != self.service_unit.read_bytes():
                raise ValueError("Installed systemd unit has local changes; reconcile them before deployment")
        if action == 'uninstall':
            return
        self.network()
        account = self.run(['getent', 'passwd', SERVICE_USER], capture_output=True, text=True)
        if account.returncode == 0:
            if account.stdout.strip().split(':')[5] != str(self.destination):
                raise ValueError("Existing lmcraft account has a different home; inspect before proceeding")
        elif account.returncode != 2:
            raise ValueError("Unable to inspect the lmcraft service account")
        elif shutil.which('/usr/sbin/useradd') is None:
            raise ValueError("Missing required executable: /usr/sbin/useradd")
        for name in ('data', 'data/lmcraft.db', 'data/lmcraft.db.new', 'conf', 'conf/bootstrap-credentials'):
            reject_symlinks(self.destination / name)

    def stop_service(self, previous: list[str] | None) -> None:
        if previous and self.service_unit.exists():
            self.run(['systemctl', 'stop', SERVICE_NAME], check=True)

    def activate_service(self) -> None:
        account = self.run(['getent', 'passwd', SERVICE_USER], capture_output=True, text=True)
        if account.returncode == 2:
            self.run(['/usr/sbin/useradd', '--system', '--user-group', '--home-dir', str(self.destination),
                      '--no-create-home', '--shell', '/usr/sbin/nologin', SERVICE_USER], check=True)
        config = self.destination / NETWORK_CONFIG
        if not config.exists():
            content = ''.join(f'{key}={value}\n' for key, value in DEFAULT_NETWORK.items())
            self.atomic_write(config, content.encode())
        data = self.destination / 'data'
        data.mkdir(exist_ok=True, mode=0o750)
        database = data / 'lmcraft.db'
        if not database.exists():
            self.bootstrap_world(database)
        shutil.chown(data, SERVICE_USER, SERVICE_USER)
        for path in data.iterdir():
            if path.is_file():
                shutil.chown(path, SERVICE_USER, SERVICE_USER)
                path.chmod(0o640)
        self.run(['systemd-analyze', 'verify', str(self.destination / 'deploy/lmcraft.service')], check=True)
        self.atomic_write(self.service_unit, (self.destination / 'deploy/lmcraft.service').read_bytes())
        self.run(['systemctl', 'daemon-reload'], check=True)
        self.run(['systemctl', 'enable', '--now', SERVICE_NAME], check=True)
        deadline = time.monotonic() + HEALTH_TIMEOUT
        while time.monotonic() < deadline:
            result = self.run([str(self.destination / 'scripts/check-health')],
                              env={**os.environ, **self.network()}, capture_output=True, text=True)
            if result.returncode == 0:
                self.run(['systemctl', 'is-active', '--quiet', SERVICE_NAME], check=True)
                print(result.stdout.strip())
                return
            time.sleep(1)
        self.run(['systemctl', 'stop', SERVICE_NAME], check=True)
        raise ValueError("LMCraft did not produce a welcome banner; inspect journalctl -u lmcraft.service")

    def bootstrap_world(self, database: Path) -> None:
        credentials = self.destination / 'conf/bootstrap-credentials'
        if credentials.exists():
            password = credentials.read_text().splitlines()[1].removeprefix('Password: ')
        else:
            password = secrets.token_urlsafe(24)
            self.atomic_write(credentials, f'Account: Wizard\nPassword: {password}\n'.encode(), 0o600)
        # Send the secret on stdin, never in argv, the journal, or the public guide.
        salt = '$6$' + secrets.token_hex(8) + '$'
        commands = (';;#2.password = crypt(' + json.dumps(password) + ', ' + json.dumps(salt) +
                    '); return "LMCraft bootstrap complete";\nquit\n')
        prepared = database.with_suffix('.bootstrap')
        result = self.run([str(self.destination / 'bin/moo'), '-e', str(self.checkout / CORE_FILE),
                           str(prepared), '-a', '127.0.0.1', '0'],
                          input=commands, capture_output=True, text=True, timeout=60)
        if (result.returncode != 0 or '=> "LMCraft bootstrap complete"' not in result.stdout
                or not prepared.is_file()):
            raise ValueError("LambdaCore initialization failed before exposing the service")
        prepared.replace(database)

    def remove_service(self) -> None:
        if self.service_unit.exists():
            self.run(['systemctl', 'disable', '--now', SERVICE_NAME], check=True)
            self.service_unit.unlink()
            self.run(['systemctl', 'daemon-reload'], check=True)

    def installed_files(self) -> list[str] | None:
        manifest = self.destination / MANIFEST
        reject_symlinks(manifest)
        if not manifest.exists():
            if self.destination.exists():
                raise ValueError("Installation directory exists without an ownership manifest; inspect it before proceeding")
            return None
        data = json.loads(manifest.read_text())
        if (not isinstance(data, dict) or data.get('project') != PROJECT_NAME
                or not isinstance(data.get('files'), list)):
            raise ValueError("Installation ownership manifest does not match this project")
        if type(data.get('venv_owned', False)) is not bool:
            raise ValueError("Installation manifest has invalid virtual environment ownership")
        names = [relative_path(name) for name in data['files']]
        if (len(names) != len(set(names))
                or self.version_file not in names and not (not names and data.get('removed') is True)):
            raise ValueError("Installation ownership manifest has invalid files")
        for name in [*names, VERSION_MARKER]:
            path = self.destination / name
            reject_symlinks(path)
            if path.exists() and not path.is_file():
                raise ValueError(f"Managed file is no longer a regular file: {path}")
        return names

    def source_files(self) -> list[str]:
        names = {relative_path(name) for name in COPY_FILES}
        if REQUIREMENTS_FILE is not None:
            names.add(relative_path(REQUIREMENTS_FILE))
        for name in COPY_TREES:
            folder = self.checkout / relative_path(name)
            reject_symlinks(folder)
            if not folder.is_dir():
                raise ValueError(f"Missing source directory: {name}")
            for path in folder.rglob('*'):
                if '__pycache__' in path.parts or VENV_DIR in path.parts or path.suffix in ('.pyc', '.pyo'):
                    continue
                reject_symlinks(path)
                if path.is_file():
                    names.add(relative_path(path.relative_to(self.checkout).as_posix()))
        if self.version_file not in names:
            raise ValueError("Deployment must include readable CMDB constants")
        for name in names:
            source = self.checkout / name
            reject_symlinks(source)
            if name == GENERATED_BINARY and source.exists() and not source.is_file():
                raise ValueError(f"Generated executable target is not a regular file: {name}")
            if name != GENERATED_BINARY and not source.is_file():
                raise ValueError(f"Missing source file: {name}")
            target = self.destination / name
            reject_symlinks(target)
            if target.exists() and not target.is_file():
                raise ValueError(f"Managed file target is not a regular file: {target}")
        return sorted(names)

    def plan(self, action: str) -> tuple[list[str] | None, list[str]]:
        if not DEPLOYMENT_READY:
            raise ValueError("Deployment is not configured: implement provisioning, lifecycle, and health checks before enabling it")
        previous = self.installed_files()
        if action == 'upgrade' and not previous:
            raise ValueError("No installation found; run install.sh first")
        current = [] if action == 'uninstall' else self.source_files()
        if previous is not None:
            for name in set(current) - set(previous):
                if (self.destination / name).exists():
                    raise ValueError(f"New managed file would overwrite an unowned file: {name}")
        self.preflight_python(action)
        self.preflight_service(action, previous)
        if action != 'uninstall':
            self.validate_build_inputs()
            self.missing_packages()
        return previous, current

    def venv_owned(self) -> bool:
        manifest = self.destination / MANIFEST
        return manifest.is_file() and json.loads(manifest.read_text()).get('venv_owned') is True

    @staticmethod
    def python_environment() -> dict[str, str]:
        environment = os.environ.copy()
        for variable in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV',
                         'PIP_TARGET', 'PIP_PREFIX', 'PIP_USER'):
            environment.pop(variable, None)
        environment['PYTHONNOUSERSITE'] = '1'
        return environment

    def preflight_python(self, action: str) -> None:
        venv = self.destination / VENV_DIR
        reject_symlinks(venv)
        if venv.exists() and not venv.is_dir():
            raise ValueError(f'Virtual environment path is not a directory: {venv}')
        if action == 'uninstall' or REQUIREMENTS_FILE is None:
            return
        requirements = self.checkout / relative_path(REQUIREMENTS_FILE)
        if not requirements.is_file():
            raise ValueError(f'Missing Python dependency manifest: {REQUIREMENTS_FILE}')
        for entry in requirements.read_text().splitlines():
            entry = entry.strip()
            if (entry.startswith(('-e ', '--editable')) or '/opt/dev/' in entry):
                raise ValueError('Production Python dependencies must not use editable or /opt/dev installs')
        if venv.exists():
            if not self.venv_owned():
                raise ValueError(f'Refusing an unowned virtual environment: {venv}')
            configuration = venv / 'pyvenv.cfg'
            binary = venv / 'bin/python'
            reject_symlinks(configuration)
            reject_symlinks(binary.parent)
            if (not configuration.is_file() or not binary.is_file()
                    or '/opt/dev/' in configuration.read_text()
                    or '/opt/dev/' in str(binary.resolve())):
                raise ValueError(f'Production virtual environment is incomplete or references /opt/dev: {venv}')
        host_python = Path(SYSTEM_PYTHON)
        if (not host_python.is_absolute() or '/opt/dev/' in SYSTEM_PYTHON
                or host_python.is_relative_to(self.destination)
                or host_python.is_relative_to(self.checkout)
                or host_python.resolve().is_relative_to(self.checkout)
                or host_python.resolve().is_relative_to(self.destination)
                or '/opt/dev/' in str(host_python.resolve())
                or (host_python.parent.parent / 'pyvenv.cfg').exists()):
            raise ValueError('SYSTEM_PYTHON must be a host interpreter outside development and deployed environments')
        if shutil.which(SYSTEM_PYTHON) is None:
            raise ValueError(f'Missing host Python interpreter: {SYSTEM_PYTHON}')
        self.run([SYSTEM_PYTHON, '-B', '-c', 'import venv, ensurepip'],
                 check=True, env=self.python_environment(), capture_output=True,
                 text=True, timeout=30)

    def prepare_python(self) -> None:
        if REQUIREMENTS_FILE is None:
            return
        venv = self.destination / VENV_DIR
        python = venv / 'bin/python'
        environment = self.python_environment()
        if not venv.exists():
            self.run([SYSTEM_PYTHON, '-m', 'venv', str(venv)],
                     check=True, env=environment, timeout=120)
        self.run([str(python), '-m', 'pip', 'install', '--upgrade',
                  '-r', str(self.destination / REQUIREMENTS_FILE)],
                 check=True, cwd=self.destination, env=environment, timeout=300)
        self.run([str(python), '-m', 'pip', 'check'],
                 check=True, cwd=self.destination, env=environment, timeout=30)
        if RUNTIME_IMPORTS:
            # Imports run from deployed files, without a checkout or PYTHONPATH.
            self.run([str(python), '-B', '-c',
                      'from importlib import import_module; from sys import argv; '
                      '[import_module(name) for name in argv[1:]]',
                      *RUNTIME_IMPORTS],
                     check=True, cwd=self.destination, env=environment, timeout=30)

    def atomic_write(self, path: Path, content: bytes, mode: int = 0o644) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        for directory in (path.parent, *path.parent.parents):
            if not directory.is_relative_to(self.destination):
                break
            directory.chmod(0o755)
        descriptor, name = tempfile.mkstemp(prefix='.bmforge-install-', dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(content)
                os.fchmod(stream.fileno(), mode)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def remove_files(self, names: list[str]) -> None:
        for name in names:
            path = self.destination / name
            path.unlink(missing_ok=True)
            for directory in path.parents:
                if directory == self.destination:
                    break
                try:
                    directory.rmdir()
                except OSError:
                    break

    def apply(self, action: str, *, check: bool = False) -> None:
        previous, names = self.plan(action)
        if check:
            if action != 'uninstall':
                missing = self.missing_packages()
                if missing:
                    raise ValueError('Missing build packages (the real install will install them): ' + ', '.join(missing))
            print(f"{action}: checks passed for {self.destination}; no files changed.")
            return
        if action == 'uninstall':
            if previous is not None:
                self.remove_service()
                self.remove_files(previous)
                venv = self.destination / VENV_DIR
                reject_symlinks(venv)
                if venv.is_dir() and self.venv_owned():
                    shutil.rmtree(venv)
                (self.destination / VERSION_MARKER).unlink(missing_ok=True)
                (self.destination / MANIFEST).unlink()
                try:
                    self.destination.rmdir()
                except OSError:
                    # Remember that retained state belongs to this project so
                    # repeated removal or reinstallation can recognize it.
                    removed = {'project': PROJECT_NAME, 'files': [], 'removed': True}
                    self.atomic_write(self.destination / MANIFEST, (json.dumps(removed, indent=2) + '\n').encode())
            print(f"Removed managed {PROJECT_NAME} files; unowned files and persistent data are retained.")
            return
        self.prepare_build()
        self.stop_service(previous)
        self.destination.mkdir(parents=True, exist_ok=True)
        self.destination.chmod(0o755)
        # Keep ownership information for partial copies so a retry or uninstall can
        # account for new files. Advance the successful-version marker only last.
        owned = sorted(set(previous or ()) | set(names))
        previous_venv = self.venv_owned() if previous is not None else False
        ownership = {'project': PROJECT_NAME, 'files': owned,
                     'service_unit': str(self.service_unit),
                     'venv_owned': REQUIREMENTS_FILE is not None or previous_venv}
        self.atomic_write(self.destination / MANIFEST, (json.dumps(ownership, indent=2) + '\n').encode())
        # Existing managed files may change before success; this is not rollback.
        for name in [item for item in names if item != self.version_file]:
            source = self.checkout / name
            mode = 0o755 if source.stat().st_mode & 0o111 else 0o644
            self.atomic_write(self.destination / name, source.read_bytes(), mode)
        self.prepare_python()
        self.remove_files(sorted(set(previous or ()) - set(names)))
        self.atomic_write(self.destination / self.version_file, (self.checkout / self.version_file).read_bytes())
        ownership['files'] = names
        self.atomic_write(self.destination / MANIFEST, (json.dumps(ownership, indent=2) + '\n').encode())
        self.activate_service()
        self.atomic_write(self.destination / VERSION_MARKER, (self.metadata['VERSION'] + '\n').encode())
        print(f"{action}: {PROJECT_NAME} {self.metadata['VERSION']} deployed to {self.destination}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'upgrade', 'uninstall'))
    parser.add_argument('--check', action='store_true', help='Validate the operation without changing files')
    args = parser.parse_args()
    if not args.check and os.geteuid() != 0:
        parser.error('Run deployment as root; --check and --help do not require root')
    try:
        Installation(Path(__file__).resolve().parents[1]).apply(args.action, check=args.check)
    except (OSError, ValueError, TypeError, SyntaxError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Deployment failed: {error}\n")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

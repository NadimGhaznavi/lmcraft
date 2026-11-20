---
title: "Build and installation commands"
lang: en
locale: en-US
language_name: English
translation_key: lmcraft-installation
---

LMCraft was compiled and installed on **19 November 2026**, on Debian 13
(amd64), using the supplied **LambdaMOO 1.9.0alpha** distribution. The installed
world is the standard **LambdaCore, 17 May 2004**, obtained from the
[official LambdaMOO archive](https://lambda.moo.mud.org/pub/MOO/).

The upstream `MOO-1.9.0alpha/` directory is read-only. Configuration, compilation,
staging, documentation and deployment tooling are all outside that directory.
Production runs independently of the development checkout.

## Build prerequisites

The host already provided GCC, make, Autoconf, Python 3, curl, systemd and the
development headers needed by the default ASCII build. The first configure
attempt stopped at `configure: error: We need gperf`; neither gperf nor a
yacc-compatible parser generator was installed. These exact commands added the
two missing build tools:

```sh
cd /opt/dev/lmcraft
sudo -n apt-get update
sudo -n apt-get install -y bison gperf
```

This installed Bison `3.8.2` and gperf `3.2.1`. No optional Unicode, XML or Waif
dependencies were added. No Autoconf regeneration was needed: the supplied
distribution includes `configure`, `parser.c` and `keywords.c`.

## Configure and compile outside the source tree

The first attempt used `../../MOO-1.9.0alpha/configure
--srcdir=../../MOO-1.9.0alpha` from `build/moo/` and failed on the missing
prerequisites above. After installing those tools and choosing LambdaCore, the
successful build used these exact commands:

```sh
cd /opt/dev/lmcraft
mkdir -p build/moo
cd /opt/dev/lmcraft/build/moo
../../MOO-1.9.0alpha/configure --srcdir=../../MOO-1.9.0alpha --enable-sz=i32,bq32
make -j2
cd /opt/dev/lmcraft
mkdir -p scripts lmcraft/constants bin deploy tests pages
install -m 0755 build/moo/moo bin/moo
```

`--enable-sz=i32,bq32` follows the supplied upstream README's legacy database
configuration: 32-bit MOO integers and historical 32-bit byte-quota accounting.
This avoids changing LambdaCore's arithmetic and quota assumptions. The server
itself is an amd64 executable. A future move to 64-bit MOO integers requires a
world compatibility review; plan that change before 2038. Networking uses
BSD/TCP, with outbound MOO connections disabled by default.

`build/` and the staged `bin/moo` are ignored by Git. No build products are
written into or checked into the upstream source directory.

## Download and identify LambdaCore

```sh
cd /opt/dev/lmcraft
mkdir -p downloads
curl --fail --location --show-error --output downloads/LambdaCore-17May04.db https://lambda.moo.mud.org/pub/MOO/LambdaCore-17May04.db
sha256sum downloads/LambdaCore-17May04.db
```

The downloaded file's SHA-256 was:

```text
e453a0d4f837db9969e2fa00250c3a58aafcf0d843d96495c1dd81924ebf4747
```

The installer pins this checksum and refuses a different seed database. This
records the exact downloaded bytes; it is not an upstream signed checksum.
The downloaded seed remains outside Git and is never used as the live world.

## Prepare and validate the deployment tooling

The installer and wrappers were adapted from the project's pinned BMForge
templates. The installation contract is `bmforge.installation` **0.1.3**, pinned
at BMForge commit `7554b12a17332876f69d845fa752c4945cf6a3a0`.

```sh
cd /opt/dev/lmcraft
python3 .agents/bmforge/manage.py check --project .
chmod +x scripts/install.sh scripts/upgrade.sh scripts/uninstall.sh scripts/run-moo scripts/check-health
python3 -B scripts/check-cmdb.py --name LMCraft lmcraft/constants/DLMCraft.py
bash -n scripts/install.sh scripts/upgrade.sh scripts/uninstall.sh scripts/run-moo scripts/check-health
scripts/install.sh --help
python3 -B -m unittest discover -s tests -v
sudo -n scripts/install.sh --check
```

The four lifecycle tests passed. They exercise real LambdaCore initialization
with the built binary in disposable directories, simulate the systemd service
boundary, and cover repeated installation, upgrade, preserved configuration and
world data, failed activation, missing prerequisites, read-only checks,
uninstall, repeated uninstall and reinstall. Tests that create MOO sockets need
a host environment that permits sockets; they do not install a host service.

## Install and activate

```sh
cd /opt/dev/lmcraft
sudo -n scripts/install.sh
```

The installer:

1. Checks prerequisites, existing ownership and network configuration before
   changing files or stopping an installed service.
2. Installs the executable, launch/health scripts, service definition and
   readable CMDB metadata under `/opt/prod/lmcraft`.
3. Creates the system account/group `lmcraft`, with no interactive shell.
4. Seeds a new world from LambdaCore only if a live world does not already
   exist. Offline emergency mode gives `Wizard` a fresh random password hashed
   with SHA-512 crypt before public startup. The secret is supplied through
   stdin and stored only in `conf/bootstrap-credentials`, readable by root.
5. Installs `/etc/systemd/system/lmcraft.service`, reloads systemd and enables
   and starts the service. The default binding is `0.0.0.0:3333`.
6. Requires both an active service and a real MOO welcome banner before writing
   `.deployment-version`.

The successfully installed LMCraft integration version is **0.0.0** (initial
development); the executable reports upstream server version **1.9.0alpha**.
No Git release or version tag was created. This native C service needs no
Python virtual environment and has no production dependency on BMForge.

## Verify the installation

These exact operational checks were run:

```sh
sudo -n systemctl show lmcraft.service --property=ActiveState,SubState,User,Group,WorkingDirectory,ExecStart,MainPID,UnitFileState
sudo -n ss -ltnp 'sport = :3333'
sudo -n systemctl is-active lmcraft.service
sudo -n systemctl is-enabled lmcraft.service
sudo -n readlink /proc/$(systemctl show lmcraft.service --property=MainPID --value)/exe
sudo -n journalctl -u lmcraft.service -n 12 --no-pager
sudo -n stat -c '%a %U:%G %n' /opt/prod/lmcraft/conf/bootstrap-credentials /opt/prod/lmcraft/data /opt/prod/lmcraft/data/lmcraft.db /opt/prod/lmcraft/data/lmcraft.db.previous
```

The service reported `active` and `enabled`; `ss` showed the native `moo`
process listening on `0.0.0.0:3333`. `/proc` resolved its executable to
`/opt/prod/lmcraft/bin/moo`. A socket probe logged in with the generated Wizard
credential and successfully evaluated `server_version()` as `1.9.0alpha`,
without printing the password.

The actual upgrade/restart path was also run:

```sh
cd /opt/dev/lmcraft
sudo -n scripts/upgrade.sh --check
sudo -n scripts/upgrade.sh
```

It stopped the service cleanly, retained the world and credentials, promoted
the saved checkpoint on restart, and passed the welcome-banner health check.
Uninstallation was tested only in disposable fixtures; the live service was
left running.

Source integrity was checked with these exact commands (the snapshot was taken
before compilation):

```sh
cd /opt/dev/lmcraft
rg --files -0 MOO-1.9.0alpha | sort -z | xargs -0 sha256sum > build/source-before.sha256
sha256sum --check build/source-before.sha256
```

All source checksums matched. Logo work was explicitly deferred by the owner.

---

[Service operation and maintenance]({{ site.baseurl }}{% link pages/operations.md %}) ·
[Documentation index]({{ site.baseurl }}{% link index.md %})

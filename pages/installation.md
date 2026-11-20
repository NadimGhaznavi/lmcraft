---
title: "Install a new LMCraft world"
lang: en
locale: en-US
language_name: English
translation_key: lmcraft-installation
---

LMCraft installs a fresh **LambdaCore** world and runs the bundled
**LambdaMOO 1.9.0alpha** server as `lmcraft.service`, listening on TCP **3333**.
The repository contains the complete source distribution and the clean seed
database. No external source, world, or precompiled executable is downloaded.
There is no world migration or import step.

## Install on the production host

Use a Debian or Ubuntu host running systemd, with Bash and administrative
access. The installer requires Python 3.10 or newer; it installs the host's
`python3` package if Python is absent. Debian 12/13 and Ubuntu 22.04 or newer
provide a suitable default Python. Git is needed to clone or update the checkout.

For a new checkout:

```sh
cd /opt/dev
git clone https://github.com/NadimGhaznavi/lmcraft.git
cd lmcraft
sudo ./scripts/install.sh
```

For an existing checkout on a host where LMCraft has not yet been installed:

```sh
cd /opt/dev/lmcraft
git pull --ff-only
sudo ./scripts/install.sh
```

To deploy a particular release, check out its tag before running the installer.
No build directory, staged executable or downloaded seed needs to be copied
from a developer's machine.

## What the command does

1. Validates deployment ownership, configuration, the bundled source checksums
   and the seed database before changing the installation.
2. Checks Debian package status for `build-essential`, `autoconf`, `bison`,
   `gperf` and `libcrypt-dev`. If any are missing, runs:

   ```sh
   apt-get update
   apt-get install -y --no-install-recommends MISSING_PACKAGES
   ```

   `MISSING_PACKAGES` represents only the packages missing on that host; it is
   not a literal argument. If all are installed, no package-manager network
   access is needed. Python bootstrap, when needed, uses the same commands
   with `python3` as the package.

3. Creates a temporary build directory under the checkout's ignored `build/`
   directory and executes these commands there, with `SOURCE` resolved to the
   checkout's bundled `MOO-1.9.0alpha` directory:

   ```sh
   /bin/sh "$SOURCE/configure" --srcdir="$SOURCE" --enable-sz=i32,bq32
   make -j2
   ```

4. Smoke-tests the compiled server in offline emergency mode: it must report
   `1.9.0alpha` and use the intended 32-bit integer arithmetic. Stages the
   executable at ignored `bin/moo` only after that succeeds.
5. Deploys the executable, launch scripts, systemd unit and readable BMForge
   version/ownership metadata to `/opt/prod/lmcraft`.
6. Creates the `lmcraft` system account and initializes a new database from
   the bundled clean LambdaCore seed. Assigns a random Wizard password using
   SHA-512 crypt before the service accepts clients.
7. Enables and starts `lmcraft.service` on `0.0.0.0:3333` (all IPv4 interfaces),
   then verifies an active service and an actual MOO welcome banner before
   recording installation success in `.deployment-version`.

The source directory is read only during installation. All generated build
files live outside it; the installed server has no runtime dependency on the
development checkout. Compiler and package failures occur before an existing
service is stopped or its deployed files are replaced.

## Bundled inputs

| Input | Repository location |
| --- | --- |
| Original LambdaMOO 1.9.0alpha distribution | `MOO-1.9.0alpha/` |
| Checksums for all upstream source files | `deploy/moo-source.sha256` |
| Unmodified LambdaCore, 17 May 2004 | `deploy/LambdaCore-17May04.db` |

The source is the existing supplied distribution, preserved byte for byte,
including its original copyright notices and build files. The seed's SHA-256 is:

```text
e453a0d4f837db9969e2fa00250c3a58aafcf0d843d96495c1dd81924ebf4747
```

The seed contains LambdaCore's standard foundation objects and commands. Each
new host starts with its own fresh copy and private Wizard credential; no live
world or credential is included in Git. Build flags retain LambdaCore's
historical integer and quota behavior. Review a move to 64-bit MOO integers
before 2038.

## Check and verify

On a fresh target, these checks can run without installation privileges:

```sh
./scripts/install.sh --help
./scripts/install.sh --check
```

`--check` is read only: it does not install packages, compile, create build
directories or change services. It reports missing build packages with a
nonzero status; the actual `sudo ./scripts/install.sh` installs them. A passing
check verifies local prerequisites and inputs, not future compilation or startup.
Use `sudo ./scripts/install.sh --check` when checking an existing installation
whose private world directory is not readable by your account.

After installation:

```sh
sudo systemctl status lmcraft.service
sudo ss -ltnp 'sport = :3333'
sudo /opt/prod/lmcraft/scripts/check-health
sudo cat /opt/prod/lmcraft/conf/bootstrap-credentials
```

Use the installation host's address and port 3333 in a MOO client. Log in as
`connect Wizard PASSWORD`, using the private password above. The Pages hostname
serves documentation; client connectivity uses the production host's address.

## Repeated installation and lifecycle

The supported first-install workflow creates a new world. Repeating the command
preserves an existing installation's database and credentials; it never resets
or imports a world. This prevents an accidental second invocation from destroying
data. Existing databases from other installations are not a supported input.

The existing `upgrade.sh` rebuilds from the same bundled source before replacing
managed code. `uninstall.sh` stops and removes the managed service and code while
retaining data and configuration; it needs no compiler, source tree or seed.
See [service operation and maintenance]({{ site.baseurl }}{% link pages/operations.md %}).

The initial manual build and exact commands used to validate the first service
remain in the [build record]({{ site.baseurl }}{% link pages/build-record.md %}).

---

[Documentation index]({{ site.baseurl }}{% link index.md %})

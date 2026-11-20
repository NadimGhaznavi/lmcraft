# LMCraft

LMCraft packages the supplied native LambdaMOO server for a new LambdaCore world.
The canonical application name is `LMCraft`, package/repository slug `lmcraft`,
and installation root `/opt/prod/lmcraft`. Literal version and CMDB declarations
live in `lmcraft/constants/DLMCraft.py`.

## Scope and source ownership

- Keep `MOO-1.9.0alpha/` read-only and byte-for-byte unchanged. It is vendored
  upstream code, not generated LMCraft Python code. Verify it against
  `deploy/moo-source.sha256`; generate all build output outside that directory.
- Use the repository's bundled source and clean `deploy/LambdaCore-17May04.db`.
  Installation provisions missing Debian/Ubuntu build packages, compiles in an
  isolated `build/` directory, and deploys a fresh world on TCP 3333. No source
  download, existing-world migration or import workflow is part of this product.
- Preserve the native C runtime and established Bash/Python deployment tooling.
  BMForge architecture and localization rules apply to new application-owned
  features; they do not authorize rewriting or translating upstream C or MOO code.
  Do not add unused application layers, a Python runtime environment, database,
  HTTP server or other infrastructure merely to resemble a greenfield scaffold.
- Keep live world data, credentials, generated executables and build output out
  of Git. Repeated lifecycle operations must not erase persistent data.
- The development-host `lmcraft.service` is intentionally stopped and disabled.
  Do not reactivate it while preparing releases or validating this repository.
  Use disposable installation fixtures and local bare remotes for tests.

## Working commands

- `python3 -B scripts/check-cmdb.py --name LMCraft lmcraft/constants/DLMCraft.py`
- `bash -n scripts/install.sh scripts/upgrade.sh scripts/uninstall.sh scripts/lifecycle.sh scripts/new-release.sh`
- `python3 -B -m unittest discover -s tests -v`
- `sha256sum --check --quiet deploy/moo-source.sha256`

The tests compile native code and open ephemeral localhost sockets. They must
have socket access, but must not deploy a real host service or publish real refs.
`--help` and lifecycle `--check` are read-only; checking an existing protected
installation may need `sudo` for read access.

## Documentation

Use `index.md` and guides under `pages/` with the pinned BMForge GitHub Pages
skill. Keep the shared dark theme, English metadata and stable translation keys.
The owner explicitly deferred logo work. Build the site on GitHub; do not add a
local Jekyll toolchain. The release and installation guides describe separate
operations: publishing a Git tag does not deploy the production server.

## Pinned BMForge engineering instructions

This project uses **pinned BMForge Codex skills**. These are project-owned copies,
not live imports from BMForge or another application.

Before the first BMForge-related edit in a Codex session, run the **read-only**,
**offline** update check from the repository root:

    python3 .agents/bmforge/manage.py check --project .

If this project's policy prohibits all Git commands, use the alternative:

    python3 .agents/bmforge/manage.py verify --project .

verify checks only local pinned-skill and manager hashes, with no Git, network or
writes; it does not check whether newer upstream skills exist.

The check reads a clean local BMForge main checkout at
~/.cache/bmforge-upstream (override with BMFORGE_SOURCE or --source).
It never fetches or clones. Refresh that checkout separately with
'git pull --ff-only', outside this check. "CURRENT" means current as of the
reported cached source revision, not necessarily the newest GitHub commit.
Report available changes or an unavailable check to the user. **Do not apply
updates**, reinstall skills, or replace approved technologies without explicit
user authorization. Continue using the pinned skills unless instructed otherwise.

Read `.agents/skills/bmforge-project/SKILL.md` for architecture. Every new app
also follows the pinned `bmforge-constants`, `bmforge-localization` and
`bmforge-installation` skills: centralize programmatic identifiers, prepare
English localization keys from its first user-facing feature, and implement
the installation lifecycle for the actual application before the first release.
Add translations only when requested, never by guessing. Invoke other
components as needed.
Follow each selected skill's local
`references/specification.md` and approved module inventory. Never invent another
framework, database driver or plotting library as a shortcut.

Component selection and application-specific behaviour belong to this project's
requirements. A pinned skill is an instruction bundle, not executable app code.

For applications with more than one service, create an executable
`scripts/services` supporting `start` and `stop`. Run the application's
start/stop commands sequentially in an explicit order. Keep it simple;
no dependency awareness is required.

Implementation authorization gate: discussion, brainstorming, design and
proposed specifications do not authorize implementation. Read-only investigation
is permitted, but do not modify project files (including code, tests,
configuration or documentation), install dependencies or perform other
mutating work until the user explicitly authorizes the agreed scope.
A direct request to implement or fix counts; no magic words are required.
Once authorized, complete that scope, its tests and its changelog without
asking about every file. Pause for unapproved dependencies, architecture
or material scope expansion. Permission to implement does not authorize
commits, pushes, releases or deployments.

For EVERY completed logical change, including small code, tests, documentation,
configuration and maintenance work, update `CHANGELOG.md` under the single
`## [Unreleased]` heading before reporting completion or committing. Do not
wait for the release. Add or refresh one `### Summary` for each meaningful
feature, fix or operational improvement, even if only one change has occurred.
Maintain one Summary heading per section. Follow the pinned
`.agents/skills/bmforge-project/references/changelog-maintenance.md` guide.

This existing application has completed install/upgrade/uninstall tooling and
the canonical `scripts/new-release.sh`. Preserve the configured installer;
never replace it with deployment-disabled bootstrap stubs. Successful installs
must create the application-owned BASE_DIR, ownership manifest and last-successful
`.deployment-version` only after verification.

The `main`, `dev` and feature branches already exist. Preserve them and inspect
their ancestry before release work. Do not run `init` or `setup-branches` here:
the repository uses BMForge's existing-project attachment, recorded honestly
in `.agents/bmforge/lock.json`. Never rewrite that provenance to bypass a manager
guard. Do not commit, tag, push, publish a release or deploy without user
authorization. Read the pinned release-setup and creating-a-release references
before using `scripts/new-release.sh`.

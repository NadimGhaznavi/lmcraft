---
title: "BMForge project setup"
lang: en
locale: en-US
language_name: English
translation_key: lmcraft-bmforge
---

LMCraft uses project-local BMForge skills for engineering instructions,
application identity, installation, releases and GitHub Pages. This is an
adoption of the existing native LambdaMOO application: the supplied upstream
source stays unchanged and the deployed server remains a C executable.

## Project identity and tooling

| Item | LMCraft configuration |
| --- | --- |
| Canonical name | `LMCraft` |
| Repository/package slug | `lmcraft` |
| Production root | `/opt/prod/lmcraft` |
| Version and CMDB metadata | `lmcraft/constants/DLMCraft.py` |
| Project engineering instructions | `AGENTS.md` |
| Installation lifecycle | `scripts/install.sh`, `upgrade.sh`, `uninstall.sh` |
| Release publication | `scripts/new-release.sh` |
| Change history | `CHANGELOG.md` |
| Release branches | `main`, `dev`, and `feat/maint-*` |
| Documentation | Shared BMForge dark theme and GitHub Pages workflow |

The lifecycle scripts are implemented and tested. They own the installed
manifest and successful-version marker, and use the repository's source and
new-world seed. The release script updates literal version/codename metadata,
merges through `dev` to `main`, and publishes an annotated tag after interactive
confirmation. See [releases]({{ site.baseurl }}{% link pages/releases.md %}) and
[installation]({{ site.baseurl }}{% link pages/installation.md %}).

## Pinned skills

The existing project attachment pins BMForge commit
`7554b12a17332876f69d845fa752c4945cf6a3a0`:

| Skill | Specification |
| --- | --- |
| `bmforge-project` | `0.1.0` |
| `bmforge-constants` | `0.1.0` |
| `bmforge-localization` | `0.1.0` |
| `bmforge-installation` | `0.1.3` |
| `bmforge-github-pages` | `0.1.0` |

`.agents/bmforge/lock.json` records the existing-project attachment, manager
checksum and skill fingerprints. That provenance is retained; rerunning the
new-project initializer would overwrite working project-specific tooling.
The existing release branches are reused rather than recreated. New authored
features follow their applicable pinned contracts; the immutable upstream C
source is not converted to a new Python application architecture.

BMForge supplies instructions and copied templates, with no production runtime
dependency. Its localization skill applies to future application-owned UX;
documentation currently uses the shared theme's English language support.
Logo work remains deferred by the owner.

## Check the project

From the repository root:

```sh
python3 .agents/bmforge/manage.py check --project .
python3 .agents/bmforge/manage.py verify --project .
python3 -B scripts/check-cmdb.py --name LMCraft lmcraft/constants/DLMCraft.py
bash -n scripts/install.sh scripts/upgrade.sh scripts/uninstall.sh scripts/lifecycle.sh scripts/new-release.sh
python3 -B -m unittest discover -s tests -v
sha256sum --check --quiet deploy/moo-source.sha256
```

`check` compares against a clean cached BMForge source without fetching or
updating skills. `verify` validates only the local pinned fingerprints, with no
Git or network access. Updating a pin is a separately reviewed change.

Tests use disposable installation directories, ephemeral localhost sockets
and local bare Git remotes. Preparing this setup neither publishes a release
nor reactivates the stopped development-host service.

---

[Documentation index]({{ site.baseurl }}{% link index.md %})

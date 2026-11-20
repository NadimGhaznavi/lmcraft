---
title: "Create a release"
lang: en
locale: en-US
language_name: English
translation_key: lmcraft-releases
---

Use `scripts/new-release.sh` to publish a version of LMCraft through the standard
BMForge `feature → dev → main` workflow. It is adapted from the project's pinned
BMForge template. Choose the version and release message when you are ready.

## Prepare

Commit the completed feature, including its changelog entry and the release
script. Start on a clean feature branch, with local `main` and `dev` containing
their remote counterparts. `main` must be an ancestor of `dev`, and `dev` must
be an ancestor of the feature branch.

```sh
./scripts/new-release.sh --help
```

The script checks executable install, upgrade and uninstall entry points,
literal CMDB metadata, branch ancestry, changelog structure and tag/branch
collisions. It fetches refs from `origin` before asking for confirmation.

## Publish

For example, to publish version `0.1.0` with the codename `First world`:

```sh
./scripts/new-release.sh 0.1.0 "First world"
```

Use a semantic version without a leading `v`. The message becomes
`CMDB_CODENAME`. Review the displayed branch, tag, message, next feature branch
and remote, then answer `y` in the interactive terminal to publish.

The script:

1. Merges the feature into `dev`.
2. Updates `DLMCraft.VERSION`, `CMDB_CODENAME` and the changelog release heading.
3. Commits that metadata and merges `dev` into `main`.
4. Creates an annotated `v<version>` tag and brings `dev` to the same commit.
5. Atomically pushes `main`, `dev` and the tag to `origin`.
6. Creates the next local feature branch, normally `feat/maint-0.1.1` after
   releasing `0.1.0`. An optional third argument supplies a different next name.

The `main` push triggers the GitHub Pages workflow. This publishes Git refs;
the production server is deployed separately using the installation scripts.

## Deploy the selected release

For a new production installation from an existing checkout:

```sh
cd /opt/dev/lmcraft
git fetch origin --tags
git switch --detach v0.1.0
sudo ./scripts/install.sh
```

Replace `v0.1.0` with the release you chose. Use `upgrade.sh` for an already
installed LMCraft world. See the
[installation guide]({{ site.baseurl }}{% link pages/installation.md %}).

## Cancel or recover

Answering anything other than `y` or `Y` cancels before merges or release-file
changes. A preflight fetch may still update remote-tracking refs.

If a later step fails, inspect the reported step, `git status`, branch tips and
tags before retrying. The atomic push protects the remote refs as a group;
local merges, metadata commits and tags may already exist after a failed push.

The release workflow is tested using disposable repositories and local bare
remotes, including successful publication, cancellation, invalid input, missing
lifecycle entry points, tag/ancestry failures and a rejected atomic push.

---

[Documentation index]({{ site.baseurl }}{% link index.md %})

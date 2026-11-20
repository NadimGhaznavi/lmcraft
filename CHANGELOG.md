---
title: "Changelog"
lang: en
locale: en-US
language_name: English
translation_key: lmcraft-changelog
---

## [Unreleased]

### Summary

Install Autoconf automatically when missing so fresh hosts have the required
build tools. Clarify that the service listens on all IPv4 interfaces by default.

### Fixed

- Include `autoconf` in the install and upgrade prerequisites and verify its
  executable before compilation.
- Document the default `0.0.0.0:3333` listener and distinguish it from the
  loopback address used by local health probes.

## [0.1.0] - 2026-11-19 @ 20:52

### Summary

Build and install LMCraft's LambdaMOO server as a persistent systemd service on
TCP port 3333, using LambdaCore and BMForge installation metadata and lifecycle
tooling. Preserve the read-only upstream source and document the exact build,
installation and operational commands on the project's GitHub Pages site.
Fresh checkouts now install missing build prerequisites, compile the bundled
source and deploy a clean new world with one command.
The BMForge release script publishes version metadata, branches and annotated
tags through the project's existing release workflow.
Project instructions now connect the pinned skills, established application
boundaries and complete installation/release scaffold.

### Added

- Dedicated service account, protected initial Wizard credential, graceful
  checkpoint promotion, welcome-banner health verification and retained data
  across upgrades and uninstall.
- Tests for installation, upgrade, failed activation, prerequisite checks,
  ownership, uninstall and reinstall using disposable service fixtures.
- BMForge dark-theme Pages scaffold, English metadata, installation and
  operations guides, and publishing workflow. Logo deferred at the owner's request.
- Self-contained installation using the original, unchanged LambdaMOO source
  and clean LambdaCore seed in Git; automatic missing-package provisioning,
  isolated compilation and offline executable verification before deployment.
- Fresh-checkout, real client-login, missing-package and failed-build tests.
- Executable `scripts/new-release.sh` adapted from the pinned BMForge template,
  with release documentation and disposable local-remote tests for publication,
  cancellation, preflight failures and atomic-push rejection.
- Root `AGENTS.md` adapted from BMForge's canonical engineering instructions,
  plus project-setup documentation identifying the existing attachment, pinned
  standards, lifecycle entry points, release branches and validation commands.

### Changed

- Installation documentation now leads with `sudo ./scripts/install.sh` from
  a clean checkout; the exact initial manual commands remain in a build record.
- The original test service was stopped and disabled for deployment on a
  separate production host. No migration or world import is implemented.

---

[Documentation index]({{ site.baseurl }}{% link index.md %})

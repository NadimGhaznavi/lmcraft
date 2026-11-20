---
title: "Changelog"
lang: en
locale: en-US
language_name: English
translation_key: lmcraft-changelog
---

## [Unreleased]

### Summary

Build and install LMCraft's LambdaMOO server as a persistent systemd service on
TCP port 3333, using LambdaCore and BMForge installation metadata and lifecycle
tooling. Preserve the read-only upstream source and document the exact build,
installation and operational commands on the project's GitHub Pages site.
Fresh checkouts now install missing build prerequisites, compile the bundled
source and deploy a clean new world with one command.

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

### Changed

- Installation documentation now leads with `sudo ./scripts/install.sh` from
  a clean checkout; the exact initial manual commands remain in a build record.
- The original test service was stopped and disabled for deployment on a
  separate production host. No migration or world import is implemented.

---

[Documentation index]({{ site.baseurl }}{% link index.md %})

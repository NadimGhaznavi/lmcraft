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

### Added

- Dedicated service account, protected initial Wizard credential, graceful
  checkpoint promotion, welcome-banner health verification and retained data
  across upgrades and uninstall.
- Tests for installation, upgrade, failed activation, prerequisite checks,
  ownership, uninstall and reinstall using disposable service fixtures.
- BMForge dark-theme Pages scaffold, English metadata, installation and
  operations guides, and publishing workflow. Logo deferred at the owner's request.

---

[Documentation index]({{ site.baseurl }}{% link index.md %})

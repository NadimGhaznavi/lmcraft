---
title: "Service operation and maintenance"
lang: en
locale: en-US
language_name: English
translation_key: lmcraft-operations
---

LMCraft runs as `lmcraft.service` on the installation host, listening for MOO
clients on TCP **3333**. Use that host's address with a MOO client or Telnet.
`lmcraft.osoyalce.com` is the documentation hostname; it is not a game-server
address unless a separate DNS/network arrangement provides that routing.

## Installed files

| Location | Purpose |
| --- | --- |
| `/opt/prod/lmcraft/bin/moo` | Compiled LambdaMOO executable |
| `/opt/prod/lmcraft/scripts/run-moo` | Foreground launcher and checkpoint promotion |
| `/opt/prod/lmcraft/scripts/check-health` | MOO welcome-banner probe |
| `/opt/prod/lmcraft/lmcraft/constants/DLMCraft.py` | Readable CMDB identity, version and listener defaults |
| `/opt/prod/lmcraft/.installation-manifest.json` | Ownership record for managed code and systemd unit |
| `/opt/prod/lmcraft/.deployment-version` | Last successfully installed LMCraft version |
| `/opt/prod/lmcraft/conf/lmcraft.env` | Preserved IPv4 binding and port settings |
| `/opt/prod/lmcraft/conf/bootstrap-credentials` | Root-readable initial Wizard credential |
| `/opt/prod/lmcraft/data/` | Persistent live world, checkpoints and previous database |
| `/etc/systemd/system/lmcraft.service` | Enabled systemd service |

The service runs under the `lmcraft` account. Code and configuration are owned
by root; the service may write only its `data/` directory. Logs go to journald.
The upstream source and `/opt/dev/lmcraft` are not runtime dependencies.

## Connect and administer

Connect a MOO client to the installation host on port 3333. An administrator
can retrieve the initial credential locally:

```sh
sudo cat /opt/prod/lmcraft/conf/bootstrap-credentials
```

At the MOO login prompt use `connect Wizard PASSWORD`, replacing `PASSWORD`
with that credential. Do not put it into a public issue, terminal transcript
or documentation. Normal MOO/Telnet transport is unencrypted; use an SSH tunnel
for remote Wizard access over an untrusted network. The bootstrap credential
file is not automatically updated after an in-world password change.

```sh
sudo systemctl status lmcraft.service
sudo journalctl -u lmcraft.service -f
sudo systemctl restart lmcraft.service
sudo systemctl stop lmcraft.service
sudo systemctl start lmcraft.service
sudo /opt/prod/lmcraft/scripts/check-health
```

The health script defaults to port 3333; if configuration is changed, pass the
same settings as environment variables when invoking it manually. The installer
does this automatically. No host reboot was needed or performed. Local client
connectivity was verified; routing and firewalls beyond the host require their
own connectivity check from the intended client network.

## Binding and port

The installer creates this file only when missing and preserves it on upgrades:

```text
MOO_BIND_IP=0.0.0.0
MOO_PORT=3333
```

Edit `/opt/prod/lmcraft/conf/lmcraft.env` to change these values, then restart
the service. Use unquoted `KEY=value` lines, an IPv4 address and a port between
1024 and 65535. Validate settings with `scripts/upgrade.sh --check` from the
checkout before applying them through `scripts/upgrade.sh`. The CMDB constants
declare the installation defaults; keep inventory declarations consistent with
deliberate listener changes. No extra HTTP or database service is installed.

## Checkpoints and backups

LambdaMOO loads `data/lmcraft.db` and writes completed checkpoints and graceful
shutdown saves to `data/lmcraft.db.new`. Before each startup the launcher copies
the previous input to `lmcraft.db.previous`, then promotes a completed `.new`
database to `lmcraft.db`. This preserves the most recently saved world across
restarts. Partial dump files are never promoted. systemd allows up to 120
seconds for graceful shutdown.

For a consistent manual backup, stop the service and copy the entire `data/`
directory, including a `.new` file if present, to your established backup
destination; start the service afterward. Preserve `conf/` separately with
appropriate access controls. Do not copy the public seed over a live world.

## Upgrade and uninstall

After updating the checkout to the intended release, the upgrade command builds
the bundled source automatically:

```sh
cd /opt/dev/lmcraft
sudo scripts/upgrade.sh --check
sudo scripts/upgrade.sh
```

Upgrade stops the service before replacing executable files, keeps configuration
and world data, restarts the service, and updates the version marker only after
health verification succeeds. File replacement is not a transactional rollback:
if activation fails, the marker retains the last successful version, but the
new files remain for diagnosis. Correct the failure or check out the previous
release and rerun the upgrade; inspect `journalctl -u lmcraft.service` first.

To remove the installation's managed service and code:

```sh
cd /opt/dev/lmcraft
sudo scripts/uninstall.sh --check
sudo scripts/uninstall.sh
```

Uninstall disables and stops the service, removes its unit and managed code,
and removes the successful-version marker. It retains `data/`, `conf/`, the
service account that owns the world, and an ownership tombstone. Repeating
uninstall is safe. Reinstallation recognizes that retained state and preserves
the world and credential. No purge operation is provided.

---

[Documentation index]({{ site.baseurl }}{% link index.md %})

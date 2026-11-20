#!/usr/bin/env bash
# Shared host-Python bootstrap for the three existing deployment entry points.
set -euo pipefail
action=${1:?Missing lifecycle operation}
shift
case "$action" in
    install|upgrade|uninstall) ;;
    *) printf 'Unknown lifecycle operation: %s\n' "$action" >&2; exit 2 ;;
esac
check=false
for argument in "$@"; do
    case "$argument" in
        -h|--help)
            printf 'Usage: scripts/%s.sh [--check]\n' "$action"
            printf 'Run with sudo to apply; --check validates without changes.\n'
            exit 0 ;;
        --check) check=true ;;
        *) printf 'Unknown argument: %s\n' "$argument" >&2; exit 2 ;;
    esac
done
if [[ "$check" == false && "$EUID" != 0 ]]; then
    printf 'Run deployment with sudo; --check and --help do not require root.\n' >&2
    exit 1
fi
if [[ ! -x /usr/bin/python3 ]]; then
    if [[ "$check" == true || "$action" == uninstall ]]; then
        printf 'Missing /usr/bin/python3; install Python 3.10 or newer first.\n' >&2
        exit 1
    fi
    . /etc/os-release
    case "$ID" in
        debian|ubuntu) ;;
        *) printf 'Automatic installation supports Debian/Ubuntu systemd hosts.\n' >&2; exit 1 ;;
    esac
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3
fi
if ! /usr/bin/python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    printf 'Python 3.10 or newer is required.\n' >&2
    exit 1
fi
exec /usr/bin/python3 -B scripts/install.py "$action" "$@"

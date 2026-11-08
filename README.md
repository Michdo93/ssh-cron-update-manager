# SSH Cron Update Manager

Rolls out [cron-update-manager](https://github.com/Michdo93/cron-update-manager) (daily
`apt` updates at 03:00 via cron) to remote Debian-based Linux hosts over SSH.

Two tools:

| | `deploy-cron-updates.sh` (interactive) | `manager.py` (non-interactive) |
|---|---|---|
| Targets | IPv4 range (first/last address) | one host or a subnet (CIDR) |
| Discovery | SSH probe on TCP 22 (no ping) | SSH banner on TCP 22 (no ping) |
| Per device | confirm, user name, up to 3 logins | same user/password for all |
| sudo | password typed in the remote prompt | SSH password is used for `sudo -S` |
| Requires | Bash 4, `ssh`, `timeout`, `xargs`, `base64` | Python 3, `paramiko` |

Targets need an SSH server (e.g. [ssh-bootstrap-kit](https://github.com/Michdo93/ssh-bootstrap-kit)),
Internet access and an account that is root or may use `sudo`. Root login is not required.

## Interactive: `deploy-cron-updates.sh`

Works like [ssh-dns-manager](https://github.com/Michdo93/ssh-dns-manager) and
[ssh-hostname-manager](https://github.com/Michdo93/ssh-hostname-manager).

```bash
chmod +x deploy-cron-updates.sh
./deploy-cron-updates.sh
```

1. Enter the first and last IPv4 address and confirm the range.
2. The range is scanned for SSH servers (32 parallel probes; no host keys are stored while scanning).
3. For each device: confirm, enter the SSH user name, log in (up to three attempts, then the
   next device). The installer output is shown live; `sudo` asks for its password in the same
   terminal.
4. At the end the installed and the failed devices are listed.

Environment options: `SSH_PORT` (22), `CONNECT_TIMEOUT` (4), `SCAN_PARALLEL` (32),
`INSTALLER_URL` (cron-update-manager's `install.sh` on GitHub).

## Non-interactive: `manager.py`

```bash
pip install paramiko

# single host, sudo user (the SSH password is also used for sudo)
python3 manager.py --host 192.168.1.50 --user pi

# all SSH hosts of a subnet as root
python3 manager.py --subnet 192.168.1.0/24 --user root

# key login; asks for the sudo password (Enter if sudo needs none)
python3 manager.py --subnet 192.168.1.0/24 --user admin --key ~/.ssh/id_ed25519
```

Options: `--host` | `--subnet`, `--user` (default `root`), `--password`, `--key`, `--port` (22).
The exit code is `1` if at least one host failed.

## License

MIT License. Feel free to use and modify.

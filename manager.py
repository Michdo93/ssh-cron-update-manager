#!/usr/bin/env python3
"""Non-interactive variant: roll out cron-update-manager to one host or a whole subnet.

For the interactive tool (range, per-device confirmation, up to three logins per device)
use deploy-cron-updates.sh.
"""
import argparse
import getpass
import ipaddress
import os
import shlex
import socket
import sys
from concurrent.futures import ThreadPoolExecutor

try:
    import paramiko
except ImportError:
    print("[-] Error: 'paramiko' library is missing. Install it using: pip install paramiko")
    sys.exit(1)

INSTALLER_URL = os.environ.get(
    "INSTALLER_URL",
    "https://raw.githubusercontent.com/Michdo93/cron-update-manager/main/install.sh",
)

# Runs as root: directly for root, otherwise through "sudo -S" (password on stdin).
REMOTE_INSTALL = (
    "u={url}; "
    "if command -v wget >/dev/null 2>&1; then wget -qO- \"$u\"; "
    "elif command -v curl >/dev/null 2>&1; then curl -fsSL \"$u\"; "
    "else echo 'neither wget nor curl is installed' >&2; exit 97; fi | sh"
)


def ssh_port_open(ip, port=22, timeout=1.0):
    """True if something answers with an SSH banner (works when ICMP ping is blocked)."""
    try:
        with socket.create_connection((str(ip), port), timeout=timeout) as s:
            s.settimeout(timeout)
            return s.recv(4).startswith(b"SSH-")
    except OSError:
        return False


def scan_subnet(subnet_str, port):
    print(f"[*] Scanning subnet {subnet_str} for SSH servers on port {port}...")
    try:
        network = ipaddress.ip_network(subnet_str, strict=False)
    except ValueError as e:
        print(f"[-] Invalid subnet: {e}")
        return []
    hosts = list(network.hosts()) or [network.network_address]
    with ThreadPoolExecutor(max_workers=64) as pool:
        found = [str(ip) for ip, ok in zip(hosts, pool.map(lambda ip: ssh_port_open(ip, port), hosts)) if ok]
    for ip in found:
        print(f"[+] Found SSH host: {ip}")
    return found


def run(ssh, command, stdin_data=None, timeout=1800):
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    if stdin_data is not None:
        stdin.write(stdin_data)
        stdin.flush()
    stdin.channel.shutdown_write()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return stdout.channel.recv_exit_status(), out, err


def deploy_to_host(host, username, password=None, key_filename=None, port=22, attempts=3):
    """Connects via SSH, checks for Linux and runs the installer as root."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for attempt in range(1, attempts + 1):
        print(f"[*] Connecting to {host} as {username} (attempt {attempt} of {attempts})...")
        try:
            ssh.connect(host, port=port, username=username, password=password, key_filename=key_filename,
                        timeout=5, allow_agent=True, look_for_keys=key_filename is None)
            break
        except paramiko.AuthenticationException:
            print(f"[-] Authentication failed for {host}.")
            if attempt == attempts or not sys.stdin.isatty():
                return False
            password = getpass.getpass(f"SSH password for {username}@{host}: ")
        except Exception as e:  # noqa: BLE001 - report and continue with the next host
            print(f"[-] Connection error on {host}: {e}")
            return False
    try:
        _, os_name, _ = run(ssh, "uname -s")
        if os_name.strip() != "Linux":
            print(f"[-] Skipping {host}: not a Linux system (detected: {os_name.strip() or 'unknown'})")
            return False

        print(f"[+] Linux confirmed on {host}. Running cron-update-manager installer...")
        install = REMOTE_INSTALL.format(url=shlex.quote(INSTALLER_URL))
        if username == "root":
            rc, out, err = run(ssh, install)
        else:
            # -S: password from stdin, -p '': no prompt text. Without a password (key login
            # and NOPASSWD sudo) the empty line is simply ignored.
            rc, out, err = run(ssh, f"sudo -S -p '' sh -c {shlex.quote(install)}", stdin_data=(password or "") + "\n")
        if rc == 0:
            print(f"[+] Successfully configured {host}:\n{out}")
            return True
        print(f"[-] Error executing installer on {host} (exit code {rc}):\n{out}{err}")
        return False
    finally:
        ssh.close()


def main():
    parser = argparse.ArgumentParser(description="SSH Cron Update Manager - deploy update cron jobs across hosts.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--host", help="Target a single host IP or hostname")
    group.add_argument("--subnet", help="Scan a subnet for SSH servers (e.g. 192.168.1.0/24)")
    parser.add_argument("--user", default="root", help="SSH username (default: root); sudo is used for other users")
    parser.add_argument("--password", help="SSH (and sudo) password (interactive prompt if omitted)")
    parser.add_argument("--key", help="Path to SSH private key file")
    parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    args = parser.parse_args()

    password = args.password
    if not password and not args.key:
        password = getpass.getpass(f"Enter SSH password for user '{args.user}': ")
    if args.key and args.user != "root" and not password:
        password = getpass.getpass("sudo password (Enter if sudo needs none): ") or None

    hosts = [args.host] if args.host else scan_subnet(args.subnet, args.port)
    if not hosts:
        print("[-] No active hosts found or specified.")
        sys.exit(0)

    print(f"[*] Starting deployment to {len(hosts)} target(s)...")
    ok = [h for h in hosts if deploy_to_host(h, args.user, password, args.key, args.port)]
    failed = [h for h in hosts if h not in ok]
    print(f"[+] Deployment finished: {len(ok)} succeeded, {len(failed)} failed{': ' + ', '.join(failed) if failed else ''}.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import ipaddress
import os
import subprocess
import sys
import getpass
try:
    import paramiko
except ImportError:
    print("[-] Error: 'paramiko' library is missing. Install it using: pip install paramiko")
    sys.exit(1)

# The install command to run on remote hosts
INSTALL_COMMAND = "wget https://raw.githubusercontent.com/Michdo93/cron-update-manager/refs/heads/main/install.sh -O - | sh"

def ping_host(ip):
    """Simple ping check to see if a host is alive."""
    param = "-n" if os.name == "nt" else "-c"
    command = ["ping", param, "1", "-W", "1", str(ip)]
    try:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False

def scan_subnet(subnet_str):
    """Scans a subnet and returns a list of active IP addresses."""
    print(f"[*] Scanning subnet {subnet_str} for active hosts...")
    active_hosts = []
    try:
        network = ipaddress.ip_network(subnet_str, strict=False)
        for ip in network.hosts():
            if ping_host(ip):
                print(f"[+] Found active host: {ip}")
                active_hosts.append(str(ip))
    except Exception as e:
        print(f"[-] Error scanning subnet: {e}")
    return active_hosts

def deploy_to_host(host, username, password=None, key_filename=None):
    """Connects via SSH, checks if Linux, and executes the installer script."""
    print(f"[*] Connecting to {host} as {username}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(host, username=username, password=password, key_filename=key_filename, timeout=5)
        
        # Check if remote system is Linux
        stdin, stdout, stderr = ssh.exec_command("uname")
        os_name = stdout.read().decode().strip()
        if os_name != "Linux":
            print(f"[-] Skipping {host}: Not a Linux system (Detected: {os_name or 'Unknown'})")
            ssh.close()
            return

        print(f"[+] Linux confirmed on {host}. Running cron-update-manager installer...")
        
        # Execute the update manager installer
        stdin, stdout, stderr = ssh.exec_command(INSTALL_COMMAND)
        
        # Read output in real-time or finish
        out_msg = stdout.read().decode()
        err_msg = stderr.read().decode()
        
        if stdout.channel.recv_exit_status() == 0:
            print(f"[+] Successfully configured {host}:\n{out_msg}")
        else:
            print(f"[-] Error executing installer on {host}:\n{err_msg}")

    except paramiko.AuthenticationException:
        print(f"[-] Authentication failed for {host}.")
    except Exception as e:
        print(f"[-] Connection error on {host}: {e}")
    finally:
        ssh.close()

def main():
    parser = argparse.ArgumentParser(description="SSH Cron Update Manager - Deploy update cron jobs across hosts.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--host", help="Target a single host IP or hostname")
    group.add_argument("--subnet", help="Scan a subnet (e.g., 192.168.1.0/24)")
    
    parser.add_argument("--user", default="root", help="SSH username (default: root)")
    parser.add_argument("--password", help="SSH password (optional, interactive prompt if omitted)")
    parser.add_argument("--key", help="Path to SSH private key file")

    args = parser.parse_args()

    # Get password interactively if not provided via CLI and no key is given
    password = args.password
    if not password and not args.key:
        password = getpass.getpass(f"Enter SSH password for user '{args.user}': ")

    hosts_to_target = []

    if args.host:
        hosts_to_target.append(args.host)
    elif args.subnet:
        hosts_to_target = scan_subnet(args.subnet)

    if not hosts_to_target:
        print("[-] No active hosts found or specified.")
        sys.exit(0)

    print(f"[*] Starting deployment to {len(hosts_to_target)} target(s)...")
    for host in hosts_to_target:
        deploy_to_host(host, username=args.user, password=password, key_filename=args.key)

    print("[+] Deployment process finished.")

if __name__ == "__main__":
    main()

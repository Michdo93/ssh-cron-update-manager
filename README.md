# SSH Cron Update Manager

A powerful management utility written in Python that automatically rolls out your [cron-update-manager](https://github.com/Michdo93/cron-update-manager) to one or multiple remote Linux hosts over SSH. 

It supports targeting a **single host** via command-line arguments or **scanning an entire local subnet** to automatically discover and provision active Linux machines.

## Features

* **Targeted or Automated Discovery:** Update a specific IP/hostname or scan your subnet automatically.
* **Smart SSH Connection Handling:** Supports standard SSH keys or interactive password prompts via `paramiko`.
* **Linux Validation:** Automatically checks if a remote target is running Linux before attempting execution.
* **Remote Automation:** Executes your remote `cron-update-manager` installation script seamlessly via a single pipeline command (`wget ... | sh`).

## Prerequisites

Make sure you have Python 3 and the required dependencies installed:

```bash
pip install paramiko

```

## Usage

### 1. Update a single host

```bash
python3 manager.py --host 192.168.1.50 --user root

```

### 2. Scan a subnet and update all discovered Linux hosts

```bash
python3 manager.py --subnet 192.168.1.0/24 --user root

```

## License

MIT License. Feel free to use and modify.

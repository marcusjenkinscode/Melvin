# AI-OS Hardening Guide

## Overview

`harden-system` applies a layered security baseline to AI-OS installations:
1. UFW firewall
2. fail2ban SSH protection
3. sysctl kernel hardening
4. Optional: unattended-upgrades

---

## Running the Hardening Script

```bash
sudo harden-system
# Skip unattended-upgrades:
sudo harden-system --skip-upgrades
```

---

## What Is Applied

### 1. UFW Firewall

```
Default policy: deny incoming
Default policy: allow outgoing
Rule: allow SSH
```

Verify:
```bash
sudo ufw status verbose
```

**Rollback:**
```bash
sudo ufw --force reset
sudo ufw disable
```

---

### 2. fail2ban (SSH)

Configuration file: `/etc/fail2ban/jail.d/ai-os-sshd.conf`

Settings:
- `maxretry`: 5 failed attempts
- `bantime`: 3600 seconds (1 hour)
- `findtime`: 600 seconds (10 minute window)

Verify:
```bash
sudo systemctl status fail2ban
sudo fail2ban-client status sshd
```

**Rollback:**
```bash
sudo systemctl disable --now fail2ban
sudo rm /etc/fail2ban/jail.d/ai-os-sshd.conf
```

---

### 3. sysctl Hardening

Configuration file: `/etc/sysctl.d/99-ai-os-hardening.conf`

Key settings:
| Parameter | Value | Reason |
|-----------|-------|--------|
| `net.ipv4.ip_forward` | 0 | Not a router |
| `net.ipv4.conf.all.accept_redirects` | 0 | Prevent redirect attacks |
| `net.ipv4.conf.all.rp_filter` | 1 | Reverse path filtering |
| `net.ipv4.conf.all.log_martians` | 1 | Log suspicious packets |
| `net.ipv4.tcp_syncookies` | 1 | SYN flood protection |
| `fs.suid_dumpable` | 0 | Prevent SUID core dumps |
| `kernel.dmesg_restrict` | 1 | Restrict kernel log to root |
| `kernel.kptr_restrict` | 2 | Hide kernel pointers |
| `kernel.yama.ptrace_scope` | 1 | Restrict ptrace |

Verify:
```bash
sysctl -a | grep -E "(forwarding|redirects|rp_filter|syncookies|dumpable|kptr)"
```

**Rollback:**
```bash
sudo rm /etc/sysctl.d/99-ai-os-hardening.conf
sudo sysctl --system
```

---

### 4. Unattended Upgrades (Optional)

Enabled by default unless `--skip-upgrades` is passed.

**Rollback:**
```bash
sudo dpkg-reconfigure unattended-upgrades
# Select: No
```

---

## Additional Hardening Recommendations

These are not automated by `harden-system` but are recommended:

1. **Disable root SSH login:**
   ```bash
   echo "PermitRootLogin no" | sudo tee /etc/ssh/sshd_config.d/99-no-root.conf
   sudo systemctl restart sshd
   ```

2. **Use SSH key authentication only:**
   ```bash
   echo "PasswordAuthentication no" | sudo tee /etc/ssh/sshd_config.d/99-keys-only.conf
   sudo systemctl restart sshd
   ```

3. **Restrict SSH to specific users:**
   ```bash
   echo "AllowUsers youruser" | sudo tee -a /etc/ssh/sshd_config.d/99-allow-users.conf
   sudo systemctl restart sshd
   ```

4. **Encrypt the swap partition** (not covered by this scaffold).

5. **Enable AppArmor profiles** for critical services.

---

## Complete Rollback

To remove all hardening applied by `harden-system`:

```bash
# 1. UFW
sudo ufw --force reset && sudo ufw disable

# 2. fail2ban
sudo systemctl disable --now fail2ban
sudo rm -f /etc/fail2ban/jail.d/ai-os-sshd.conf
sudo systemctl restart fail2ban

# 3. sysctl
sudo rm -f /etc/sysctl.d/99-ai-os-hardening.conf
sudo sysctl --system

# 4. Unattended upgrades
sudo dpkg-reconfigure unattended-upgrades
```

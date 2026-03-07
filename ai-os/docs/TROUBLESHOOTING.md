# AI-OS Troubleshooting Guide

## Table of Contents

1. [Build Failures](#build-failures)
2. [Module System](#module-system)
3. [Model Vault](#model-vault)
4. [Hardening](#hardening)
5. [AI Inference](#ai-inference)
6. [Collecting Debug Info](#collecting-debug-info)

---

## Build Failures {#build-failures}

### `lb: command not found`

**Cause:** `live-build` is not installed.

**Fix:**
```bash
sudo apt-get install -y live-build
```

### `lb build` fails with debootstrap error

**Cause:** Network issue or missing archive area.

**Fix:**
```bash
# Test connectivity:
curl -I http://archive.ubuntu.com

# Clean and retry:
cd live-build && sudo lb clean --all && sudo lb build
```

### ISO is not produced after `lb build`

**Cause:** Build succeeded but artifact name differs by live-build version.

**Fix:**
```bash
find live-build/ -name "*.iso" -maxdepth 2
```

The `build.sh` script auto-searches for any `.iso` file in the `live-build/` directory.

### `mksquashfs: zstd not supported`

**Cause:** `squashfs-tools` package is too old (< 4.4).

**Fix:**
```bash
sudo apt-get install -y squashfs-tools
mksquashfs --version  # should be 4.4+
```

---

## Module System {#module-system}

### `activate-module: Module image not found`

```
[activate-module] ERROR: Module image not found: /opt/modules/ai-tools.squashfs
```

**Fix:**
```bash
# Build the module:
cd ai-os && bash modules/build-module-ai-tools.sh
# Copy to target:
sudo cp modules/ai-tools.squashfs /opt/modules/
```

### Module fails to mount

```
mount: /mnt/modules/ai-tools: wrong fs type, bad option, bad superblock
```

**Cause:** The squashfs file is corrupt or not a valid squashfs image.

**Fix:**
```bash
# Inspect:
file /opt/modules/ai-tools.squashfs
# Rebuild:
sudo bash modules/build-module-ai-tools.sh
```

### Cannot unmount module — `target is busy`

**Fix:**
```bash
# Find processes using the mount:
lsof /mnt/modules/ai-tools
# Kill them and retry:
sudo deactivate-module ai-tools
```

---

## Model Vault {#model-vault}

### `unlock-models: Vault config not found`

```
[unlock-models] ERROR: Vault config not found: /etc/ai-os/vault.conf
```

**Fix:** The vault has not been initialised yet.
```bash
sudo setup-model-vault --device /dev/sdb1
```

### `cryptsetup luksOpen` fails — `No key available`

**Cause:** Wrong passphrase or keyfile.

**Fix:**
```bash
# If using passphrase, retry:
sudo cryptsetup luksOpen /dev/sdb1 ai-models

# List LUKS key slots:
sudo cryptsetup luksDump /dev/sdb1 | grep -i slot
```

### `/opt/ai/models` is mounted read-only

**Cause:** Filesystem errors on the vault.

**Fix:**
```bash
# Close and check:
sudo lock-models
sudo cryptsetup luksOpen /dev/sdb1 ai-models-check
sudo e2fsck -f /dev/mapper/ai-models-check
sudo cryptsetup luksClose ai-models-check
sudo unlock-models
```

### `setup-model-vault` refuses dangerous device

**Cause:** The target device matches a known system disk path (`/dev/sda`, `/dev/nvme0n1`, `/dev/vda`).

**Fix:** Use a specific partition:
```bash
sudo setup-model-vault --device /dev/sda2   # a specific partition, not the whole disk
```

---

## Hardening {#hardening}

### UFW blocks SSH after hardening

**Cause:** SSH is allowed by `harden-system` but a custom rule may conflict.

**Fix:**
```bash
sudo ufw allow ssh
sudo ufw status verbose
```

### fail2ban bans your own IP

**Fix:**
```bash
sudo fail2ban-client set sshd unbanip <your-ip>
```

### sysctl changes break networking

**Fix:**
```bash
sudo rm /etc/sysctl.d/99-ai-os-hardening.conf
sudo sysctl --system
```

---

## AI Inference {#ai-inference}

### `ollama: command not found`

**Fix:**
```bash
sudo ai-profile cpu
```

### Ollama is very slow (CPU-only)

- Use a quantised model (e.g., `q4_0` suffix)
- Reduce context window: `ollama run --num-ctx 512 tinyllama`
- See [PERFORMANCE.md](PERFORMANCE.md) for CPU governor tuning

### Ollama does not use NVIDIA GPU

**Fix:**
```bash
# Verify driver:
nvidia-smi
# Verify CUDA in Ollama:
ollama run llama3 --verbose 2>&1 | grep -i gpu
```
If no GPU is shown, reboot and recheck.

### ROCm not detected

See [PERFORMANCE.md](PERFORMANCE.md#gpu-tuning) and the AMD ROCm official documentation.

---

## Collecting Debug Info {#collecting-debug-info}

If you cannot resolve an issue, collect a debug bundle:

```bash
bash scripts/collect-debug.sh
```

Output: `/tmp/ai-os-debug-<timestamp>.tar.gz`

**Note:** The bundle includes `/etc/ai-os/vault.conf` which contains the vault device path.
Review the archive before sharing with third parties.

# AI-OS Operations Guide

## Overview

This document covers day-to-day operations of an AI-OS system:
- Module management
- Model vault management
- AI hardware profiles
- Benchmarking

---

## Module System

AI-OS uses squashfs overlay modules stored in `/opt/modules/` and mounted at `/mnt/modules/`.

### Activate a Module

```bash
sudo activate-module ai-tools
# Mounts /opt/modules/ai-tools.squashfs -> /mnt/modules/ai-tools (read-only)
```

### Deactivate a Module

```bash
sudo deactivate-module ai-tools
```

### List Active Modules

```bash
mount | grep squashfs
```

### Build Custom Modules

```bash
# Place files in modules/root-ai-tools/ or modules/root-dev-tools/
# Then build:
bash modules/build-module-ai-tools.sh
bash modules/build-module-dev-tools.sh

# Copy the resulting .squashfs to the target system:
sudo cp modules/ai-tools.squashfs /opt/modules/
```

---

## Model Vault {#model-vault}

The AI model vault is a LUKS-encrypted volume mounted at `/opt/ai/models`.

### Initial Setup

```bash
# Using a dedicated block device:
sudo setup-model-vault --device /dev/sdb1

# Using an image file (e.g., 50 GB):
sudo setup-model-vault --device /data/models.img --size-mb 51200

# With a keyfile for automated unlock:
sudo setup-model-vault --device /dev/sdb1 --keyfile /etc/ai-os/models.key
```

You will be prompted to type `YES` to confirm the destructive format operation.

After setup, follow the printed `crypttab`/`fstab` instructions to enable auto-unlock at boot.

### Unlock the Vault

```bash
sudo unlock-models
# With keyfile:
sudo unlock-models --keyfile /etc/ai-os/models.key
```

### Lock the Vault

```bash
sudo lock-models
```

### Check Vault Status

```bash
ls /opt/ai/models/
mountpoint /opt/ai/models && echo "mounted" || echo "not mounted"
cryptsetup status ai-models
```

---

## AI Hardware Profiles {#ai-profiles}

### CPU-Only (default)

Installs minimal Python tooling and Ollama:

```bash
sudo ai-profile cpu
```

After activation:
```bash
ollama pull tinyllama
ollama run tinyllama
```

### NVIDIA GPU

Installs `ubuntu-drivers-common`, runs autoinstall, and installs Ollama:

```bash
sudo ai-profile nvidia
# NOTE: A reboot is required after driver installation.
```

After reboot:
```bash
nvidia-smi   # verify driver
ollama run llama3
```

### AMD GPU (ROCm)

AMD support is intentionally conservative. The command prints guided instructions:

```bash
ai-profile amd
```

Follow the printed steps to install ROCm manually from the official docs.

---

## Benchmarking

```bash
# Basic system info:
ai-benchmark

# Include a tiny inference timing test (requires a model to be pulled):
ai-benchmark --inference
```

---

## Useful Paths

| Path | Purpose |
|------|---------|
| `/opt/ai/models` | Encrypted model vault mount point |
| `/opt/ai/workspaces` | User AI workspaces |
| `/opt/modules` | Squashfs module images |
| `/mnt/modules` | Active module mount points |
| `/etc/ai-os/vault.conf` | Vault configuration |
| `/usr/local/bin/` | AI-OS management scripts |

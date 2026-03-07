# AI-OS Installation Guide

## Overview

AI-OS is a minimal, modular, encrypted Ubuntu 24.04 AI distribution scaffold.
It is designed to be built as a live ISO using `live-build` and installed on bare-metal or VM targets.

---

## Prerequisites

- Ubuntu 24.04 (Noble) build host (physical or VM)
- At least 20 GB free disk space for the build
- Internet access to download packages

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/marcusjenkinscode/Melvin.git
cd Melvin/ai-os
```

---

## Step 2 — Bootstrap the Build Host

Install all required build dependencies:

```bash
bash bootstrap-host.sh
# or
make bootstrap
```

This installs: `live-build debootstrap squashfs-tools xorriso syslinux-utils isolinux mtools dosfstools cryptsetup rsync curl wget jq git build-essential python3 python3-pip python3-venv`

---

## Step 3 — Build Squashfs Modules (Optional)

Build the optional AI and dev tool overlay modules:

```bash
make modules
```

Output: `modules/ai-tools.squashfs` and `modules/dev-tools.squashfs`

---

## Step 4 — Build the ISO

```bash
make iso
# or directly:
bash build.sh
```

The build process:
1. Cleans previous artifacts (`lb clean --all`)
2. Configures live-build for Ubuntu Noble amd64 iso-hybrid
3. Runs `lb build` (may take 20–60 minutes)

**Expected artifact path:**
```
live-build/live-image-amd64.hybrid.iso
```

Build log is saved to: `build.log`

---

## Step 5 — Write ISO to USB

```bash
sudo dd if=live-build/live-image-amd64.hybrid.iso of=/dev/sdX bs=4M status=progress && sync
```

Replace `/dev/sdX` with your target USB device.

---

## Step 6 — Boot and Install

1. Boot from the USB drive
2. Select **Install** from the live boot menu
3. Follow the Ubuntu installer

---

## Step 7 — Post-Installation Setup

After first boot on the installed system, run as root:

```bash
sudo bash /path/to/ai-os/scripts/install-post.sh
```

Then proceed with:
- [Setting up the model vault](OPERATIONS.md#model-vault)
- [Choosing an AI hardware profile](OPERATIONS.md#ai-profiles)
- [Hardening the system](HARDENING.md)

---

## Verification

```bash
bash scripts/verify-system.sh
```

A passing run looks like:

```
OVERALL: PASS — system looks good.
```

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.

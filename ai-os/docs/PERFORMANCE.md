# AI-OS Performance Guide

## Overview

This document covers performance tuning for AI inference workloads on AI-OS.

---

## Benchmarking

Run the built-in benchmark tool:

```bash
# System info only:
ai-benchmark

# With inference timing test (requires a model):
ai-benchmark --inference
```

The benchmark collects:
- CPU model, cores, frequency
- Total and free RAM
- Disk usage and mount status
- Active AI-OS module mounts
- Ollama version
- GPU information (NVIDIA/AMD if present)
- Optional: inference timing for a pulled model

---

## Model Selection by RAM

| Available RAM | Recommended Models |
|--------------|-------------------|
| < 8 GB | `tinyllama`, `phi3:mini` |
| 8–15 GB | `mistral:7b-instruct-q4`, `llama3:8b-q4` |
| 16–31 GB | `llama3:13b-q4`, `mistral:7b` |
| 32+ GB | `llama3:70b-q4`, larger models |

Pull a model:
```bash
ollama pull tinyllama
ollama pull mistral:7b-instruct-q4_0
```

---

## CPU Tuning

### Governor

For inference, the `performance` CPU governor reduces latency:

```bash
# Check current governor:
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# Set performance governor (requires cpufrequtils or kernel module):
sudo apt-get install -y cpufrequtils
sudo cpufreq-set -g performance
# Or for all CPUs:
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

Note: This increases power consumption.

### NUMA

On multi-socket systems, pin Ollama to the correct NUMA node:

```bash
numactl --cpunodebind=0 --membind=0 ollama run mistral
```

---

## GPU Tuning

### NVIDIA

```bash
# Check GPU utilization:
watch -n1 nvidia-smi

# Set persistence mode (reduces initialization latency):
sudo nvidia-smi -pm 1

# Set power limit (e.g., 300W for RTX 4090):
sudo nvidia-smi -pl 300
```

### AMD ROCm

```bash
# Check GPU utilization:
rocm-smi

# Set performance level:
sudo rocm-smi --setperflevel high
```

---

## Storage Tuning

### Model Vault (LUKS ext4)

The encrypted model vault at `/opt/ai/models` may add I/O overhead.

For SSD-backed vaults, you can enable `discard` (TRIM) in crypttab:

```
ai-models  /dev/sdb1  /etc/ai-os/models.key  luks,discard
```

### squashfs Module Compression

The default module compression uses zstd level 19 (maximum compression).
For faster module load times at the cost of size, reduce the compression level
in the builder scripts (e.g., `-Xcompression-level 3`).

---

## Memory Management

### Huge Pages (for large models)

```bash
# Enable transparent huge pages:
echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled

# Allocate static huge pages (example: 8192 × 2MB = 16 GB):
sudo sysctl -w vm.nr_hugepages=8192
```

### Swap

Swap can significantly slow inference. Disable it on dedicated AI nodes:

```bash
sudo swapoff -a
# To persist, comment out swap entries in /etc/fstab
```

---

## Monitoring During Inference

```bash
# CPU / RAM:
htop

# GPU (NVIDIA):
watch -n1 nvidia-smi

# Disk I/O:
iostat -x 1

# Network:
iftop
```

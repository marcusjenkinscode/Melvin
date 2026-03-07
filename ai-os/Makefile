.PHONY: bootstrap modules iso clean harden benchmark verify

# ──────────────────────────────────────────────
# Bootstrap host build dependencies
# ──────────────────────────────────────────────
bootstrap:
	bash bootstrap-host.sh

# ──────────────────────────────────────────────
# Build squashfs overlay modules
# ──────────────────────────────────────────────
modules:
	bash modules/build-module-ai-tools.sh
	bash modules/build-module-dev-tools.sh

# ──────────────────────────────────────────────
# Build the live ISO
# ──────────────────────────────────────────────
iso:
	bash build.sh

# ──────────────────────────────────────────────
# Clean build artifacts
# ──────────────────────────────────────────────
clean:
	@echo "[clean] Removing live-build artifacts..."
	cd live-build && sudo lb clean --all || true
	@echo "[clean] Done."

# ──────────────────────────────────────────────
# Apply system hardening (run on target system)
# ──────────────────────────────────────────────
harden:
	sudo live-build/config/includes.chroot/usr/local/bin/harden-system

# ──────────────────────────────────────────────
# Run AI benchmark (run on target system)
# ──────────────────────────────────────────────
benchmark:
	live-build/config/includes.chroot/usr/local/bin/ai-benchmark

# ──────────────────────────────────────────────
# Verify installed system state (run on target)
# ──────────────────────────────────────────────
verify:
	bash scripts/verify-system.sh

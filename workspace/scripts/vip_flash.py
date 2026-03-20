#!/usr/bin/env python3
"""
VIP Flash - CPH2451 (OnePlus 11 / SM8550) EDL full-firmware flash with VIP bypass.

Calls bkerler's edl.py via subprocess for each of the 6 UFS LUNs.
Avoids importing edlclient directly (libusb segfault workaround for Python 3.9/Win32).

Usage:
    python vip_flash.py [--vip] [--lun <0-5|all>] [--dryrun]

Flags:
    --vip       Force VIP-bypass loader (bkerler oppo loader).
    --lun       Flash specific LUN (0-5) or 'all' (default: all)
    --dryrun    Validate paths and print commands only, do not flash
"""
import os
import sys
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Optional, List

# config.py lives at workspace/ root
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("VIP_FLASH")

EDL_PY = config.EDL_REPO_PATH / "edl.py"


def find_edl_usb() -> bool:
    """Check if Qualcomm EDL device is present. Returns True if found."""
    try:
        import usb.core
        dev = usb.core.find(idVendor=0x05C6, idProduct=0x9008)
        return dev is not None
    except Exception as e:
        logger.warning(f"USB scan error: {e}")
    return False


def build_qfil_cmd(loader: Path, rawprogram: Path, patch: Path, imagedir: Path) -> List[str]:
    """Build the edl.py qfil command for one LUN."""
    return [
        sys.executable, str(EDL_PY),
        "--loader", str(loader),
        "--memory", "ufs",
        "qfil", str(rawprogram), str(patch), str(imagedir),
    ]


def make_edl_env() -> dict:
    """Build subprocess env with pip libusb 1.0.27 DLL prepended to PATH."""
    env = os.environ.copy()
    pip_libusb = r"C:\Users\Andrew Price\AppData\Roaming\Python\Python39\site-packages\libusb\_platform\_windows\x64"
    env["PATH"] = pip_libusb + ";" + env.get("PATH", "")
    return env


def ensure_edl_logs_dir() -> None:
    """Create edl-master logs/ directory if missing (edlclient crashes without it)."""
    logs_dir = config.EDL_REPO_PATH / "logs"
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created missing logs dir: {logs_dir}")


def flash_lun(lun: int, loader: Path, payload_dir: Path, imagedir: Path,
              dryrun: bool, env: Optional[dict] = None) -> bool:
    """Flash one UFS LUN via edl.py qfil subprocess."""
    rawprogram = payload_dir / f"rawprogram{lun}.xml"
    patch = payload_dir / f"patch{lun}.xml"

    if not rawprogram.exists():
        logger.error(f"Missing: {rawprogram}")
        return False
    if not patch.exists():
        logger.error(f"Missing: {patch}")
        return False

    cmd = build_qfil_cmd(loader, rawprogram, patch, imagedir)
    logger.info(f"--- LUN {lun} ---")
    logger.info(f"  cmd: {' '.join(cmd)}")

    if dryrun:
        logger.info(f"  [DRYRUN] skipping execution")
        return True

    if env is None:
        env = make_edl_env()
    result = subprocess.run(cmd, cwd=str(config.EDL_REPO_PATH), timeout=600, env=env)
    if result.returncode == 0:
        logger.info(f"LUN {lun}: PASS")
        return True
    else:
        logger.error(f"LUN {lun}: FAILED (returncode={result.returncode})")
        return False


def run_vip_flash(use_vip: bool, luns: List[int], dryrun: bool) -> bool:
    payload_dir = config.WORKSPACE_DIR / "payloads"
    imagedir = config.FIRMWARE_ROOT
    loader = config.VIP_LOADER_PATH if use_vip else config.LOADER_PATH

    logger.info("=== CPH2451 VIP Flash - Pre-flight ===")
    logger.info(f"edl.py        : {EDL_PY} ({'OK' if EDL_PY.exists() else 'MISSING'})")
    logger.info(f"Loader        : {loader} ({'OK' if loader.exists() else 'MISSING'})")
    logger.info(f"Firmware root : {imagedir} ({'OK' if imagedir.exists() else 'MISSING'})")
    logger.info(f"Payload dir   : {payload_dir}")
    logger.info(f"LUNs          : {luns}")
    logger.info(f"Mode          : {'DRY RUN' if dryrun else 'LIVE FLASH'}")

    if not EDL_PY.exists():
        logger.error(f"edl.py not found at {EDL_PY}")
        return False

    if not loader.exists():
        # Fallback: try the other loader
        fallback = config.LOADER_PATH if use_vip else config.VIP_LOADER_PATH
        if fallback.exists():
            logger.warning(f"Primary loader missing, falling back to: {fallback}")
            loader = fallback
        else:
            logger.error(f"No loader found. Checked:\n  {config.LOADER_PATH}\n  {config.VIP_LOADER_PATH}")
            return False

    for lun in luns:
        rp = payload_dir / f"rawprogram{lun}.xml"
        pt = payload_dir / f"patch{lun}.xml"
        logger.info(f"  LUN {lun} payloads: {'OK' if rp.exists() and pt.exists() else 'MISSING'}")

    if dryrun:
        logger.info("Dry run complete.")
        return True

    # Check USB device — wait up to 60s for device to appear
    logger.info("=== USB device check ===")
    import time
    for attempt in range(30):
        if find_edl_usb():
            break
        if attempt == 0:
            logger.info("Waiting for EDL device... (Hold Vol+ + Vol- while plugging USB)")
        time.sleep(2)
    else:
        logger.error("EDL device not detected after 60s. Aborting.")
        return False
    logger.info("EDL device found (VID:05C6 PID:9008)")

    # Flash each LUN — reset device after each flash so next LUN starts from clean sahara state
    logger.info("=== Flashing ===")
    import time
    ensure_edl_logs_dir()
    edl_env = make_edl_env()
    results = {}
    for i, lun in enumerate(luns):
        if i > 0:
            logger.info(f"Waiting 15s for device to come back in EDL mode before LUN {lun}...")
            time.sleep(15)
        results[lun] = flash_lun(lun, loader, payload_dir, imagedir, dryrun, env=edl_env)
        # After each flash (except last), send explicit reset to cleanly exit firehose
        if i < len(luns) - 1 and not dryrun:
            logger.info(f"Sending reset after LUN {lun} to cleanly exit firehose...")
            reset_cmd = [
                sys.executable, str(EDL_PY),
                "--loader", str(loader),
                "--skipresponse", "reset",
            ]
            try:
                subprocess.run(reset_cmd, cwd=str(config.EDL_REPO_PATH),
                               timeout=20, env=edl_env, capture_output=True)
            except Exception:
                pass  # reset may not respond — that's fine

    # Summary
    logger.info("=== Summary ===")
    all_ok = True
    for lun, ok in results.items():
        logger.info(f"  LUN {lun}: {'PASS' if ok else 'FAIL'}")
        if not ok:
            all_ok = False

    if all_ok:
        logger.info("ALL LUNS FLASHED OK. Device should boot on reconnect.")
    else:
        logger.error("Some LUNs failed. Check logs above.")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="CPH2451 VIP Flash via edl.py subprocess")
    parser.add_argument("--vip", action="store_true",
                        help="Force VIP-bypass loader (default: auto)")
    parser.add_argument("--lun", default="all",
                        help="LUN to flash: 0-5 or 'all' (default: all)")
    parser.add_argument("--dryrun", action="store_true",
                        help="Print commands only, do not flash")
    args = parser.parse_args()

    luns = list(range(6)) if args.lun == "all" else [int(args.lun)]

    success = run_vip_flash(
        use_vip=args.vip or config.USE_VIP_LOADER,
        luns=luns,
        dryrun=args.dryrun,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

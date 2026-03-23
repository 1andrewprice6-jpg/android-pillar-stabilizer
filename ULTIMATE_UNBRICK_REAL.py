#!/usr/bin/env python3
"""
OnePlus 11 (CPH2451) EDL Unbrick Tool
======================================
Flashes all 6 UFS LUNs in sequence via bkerler/edl (Firehose QFIL protocol).

Device:   OnePlus 11 (CPH2451)
SoC:      Qualcomm Snapdragon 8 Gen 2 (SM8550)
Firmware: 15.0.0.600 EX01 (ColorOS 15)

UFS LUN Map:
  LUN 0 - rawprogram0.xml  GPT, super, userdata, persist
  LUN 1 - rawprogram1.xml  xbl_a (bootloader slot A)
  LUN 2 - rawprogram2.xml  xbl_b (bootloader slot B)
  LUN 3 - rawprogram3.xml  cdt, ddr calibration
  LUN 4 - rawprogram4.xml  boot, tz, modem, dsp, system (MAIN FIRMWARE)
  LUN 5 - rawprogram5.xml  nvbk, modemst, oplusreserve

Prerequisites:
  pip install edl pyserial
  (or: git clone https://github.com/bkerler/edl.git ~/edl)
"""

import os
import sys
import time
import logging
import argparse
import shutil
import subprocess
from pathlib import Path

try:
    import serial.tools.list_ports
    _HAS_SERIAL = True
except ImportError:
    _HAS_SERIAL = False

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ULTIMATE_UNBRICK")

# ---------------------------------------------------------------------------
# Path discovery helpers
# ---------------------------------------------------------------------------

def find_edl_tool():
    """Find the bkerler/edl tool (edl.py or edl command) on this machine."""
    # 1. Installed as a pip command on PATH
    edl_cmd = shutil.which("edl")
    if edl_cmd:
        return edl_cmd

    # 2. Common manual install locations
    candidates = [
        Path.home() / "edl" / "edl.py",
        Path.home() / "Desktop" / "edl-master" / "edl-master" / "edl.py",
        Path.home() / "Desktop" / "edl" / "edl.py",
        Path(__file__).parent / "edl.py",
        Path(__file__).parent / "edl" / "edl.py",
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    # 3. Installed as Python package — locate the edl.py entry point
    try:
        import edlclient  # noqa: F401
        pkg_parent = Path(sys.executable).parent
        for suffix in ("edl", "edl.py"):
            candidate = pkg_parent / suffix
            if candidate.exists():
                return str(candidate)
    except ImportError:
        pass

    return None


def find_edl_port():
    """Auto-detect Qualcomm EDL device (VID=05C6, PID=9008) on a serial port."""
    if not _HAS_SERIAL:
        logger.warning("pyserial not installed — cannot auto-detect port.")
        return None
    for port in serial.tools.list_ports.comports():
        if port.vid == 0x05C6 and port.pid == 0x9008:
            logger.info(f"Auto-detected EDL device on {port.device}")
            return port.device
    return None


def wait_for_edl_device(timeout=60):
    """Poll for EDL device for up to `timeout` seconds, return port or None."""
    if not _HAS_SERIAL:
        return None
    logger.info(f"Waiting for EDL device (up to {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        port = find_edl_port()
        if port:
            return port
        time.sleep(2)
    return None


# ---------------------------------------------------------------------------
# Core flash function
# ---------------------------------------------------------------------------

def flash_lun(edl_tool, loader, firmware_dir, lun_idx, port=None, dry_run=False):
    """
    Flash one UFS LUN using: edl.py qfil rawprogram<N>.xml patch<N>.xml <dir>

    Returns True on success, False on failure.
    Skips gracefully when rawprogram/patch XML files are missing.
    """
    fw_path = Path(firmware_dir)
    rawprogram = fw_path / f"rawprogram{lun_idx}.xml"
    patch = fw_path / f"patch{lun_idx}.xml"

    if not rawprogram.exists():
        logger.info(f"LUN {lun_idx}: rawprogram{lun_idx}.xml not found — skipping")
        return True  # Non-fatal: not all firmware packages have all 6 LUNs
    if not patch.exists():
        logger.info(f"LUN {lun_idx}: patch{lun_idx}.xml not found — skipping")
        return True

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"  LUN {lun_idx}: {rawprogram.name} + {patch.name}")
    logger.info("=" * 60)

    # Build edl command
    # If edl_tool is an installed command (no .py), call it directly;
    # otherwise run it through the current Python interpreter.
    if edl_tool.endswith(".py"):
        cmd = [sys.executable, edl_tool]
    else:
        cmd = [edl_tool]

    cmd += [
        "qfil",
        str(rawprogram),
        str(patch),
        str(fw_path),
        f"--loader={loader}",
        "--memory=ufs",
        "--skipresponse",
    ]

    if dry_run:
        cmd.append("--skipwrite")

    if port:
        # Use serial port mode
        port_str = port if port.startswith("\\\\.\\") else f"\\\\.\\{port}"
        cmd += ["--serial", f"--portname={port_str}"]

    logger.info(f"CMD: {' '.join(str(c) for c in cmd)}")
    logger.info("")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )

        for line in process.stdout:
            line = line.rstrip()
            if not line:
                continue
            # Surface VIP bypass warnings clearly
            if "[VIP-BYPASS]" in line:
                logger.warning(f"  [EDL] {line}")
            elif any(kw in line.lower() for kw in ("error", "fail", "exception")):
                logger.error(f"  [EDL] {line}")
            else:
                logger.info(f"  [EDL] {line}")

        process.wait()

        if process.returncode == 0:
            logger.info(f"✓ LUN {lun_idx} flashed successfully")
            return True
        else:
            logger.error(f"✗ LUN {lun_idx} failed (exit code {process.returncode})")
            return False

    except FileNotFoundError:
        logger.error(f"EDL tool not found: {edl_tool}")
        return False
    except Exception as exc:
        logger.error(f"Unexpected error on LUN {lun_idx}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Main unbrick routine
# ---------------------------------------------------------------------------

def run_unbrick(
    port=None,
    loader=None,
    firmware_dir=None,
    edl_tool=None,
    start_lun=0,
    end_lun=5,
    dry_run=False,
    wait_device=False,
):
    """
    Complete unbrick: validates inputs, detects device, then flashes LUNs
    start_lun through end_lun (inclusive).
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("  OnePlus 11 (CPH2451) EDL Unbrick Tool")
    logger.info("  Snapdragon 8 Gen 2 (SM8550)")
    logger.info("  Firmware: 15.0.0.600 EX01 (ColorOS 15)")
    logger.info("=" * 60)

    if dry_run:
        logger.warning("DRY RUN MODE — XML will be parsed but nothing written to device")

    # Locate edl tool
    if not edl_tool:
        edl_tool = find_edl_tool()
    if not edl_tool:
        logger.error("Cannot find edl tool.")
        logger.error("  Install:  pip install edl")
        logger.error("  Or clone: git clone https://github.com/bkerler/edl.git ~/edl")
        return False
    logger.info(f"EDL tool   : {edl_tool}")

    # Validate loader
    if not loader:
        logger.error("--loader is required (path to prog_firehose_ddr.elf)")
        return False
    loader_path = Path(loader)
    if not loader_path.exists():
        logger.error(f"Loader not found: {loader}")
        return False
    logger.info(f"Loader     : {loader_path.name} ({loader_path.stat().st_size // 1024} KB)")

    # Validate firmware directory
    if not firmware_dir:
        logger.error("--firmware-dir is required")
        return False
    fw_path = Path(firmware_dir)
    if not fw_path.exists():
        logger.error(f"Firmware directory not found: {firmware_dir}")
        return False
    if not (fw_path / "rawprogram0.xml").exists():
        logger.error(f"rawprogram0.xml not found in {firmware_dir}")
        logger.error("Ensure you're pointing at the IMAGES/ folder of the firmware package.")
        return False
    logger.info(f"Firmware   : {fw_path}")

    # Detect or wait for EDL device
    if not port:
        if wait_device:
            port = wait_for_edl_device(timeout=120)
        else:
            port = find_edl_port()

    if not port:
        logger.error("No Qualcomm EDL device detected (VID=05C6, PID=9008).")
        logger.error("Steps to enter EDL mode on OnePlus 11 (CPH2451):")
        logger.error("  Software: adb reboot edl")
        logger.error("  Fastboot: fastboot oem edl")
        logger.error("  Hardware: Hold Vol Up + Vol Down + Power for 5s, plug USB")
        logger.error("  Then run with --wait-device to poll automatically.")
        return False
    logger.info(f"Port       : {port}")
    logger.info("")

    # Flash each LUN
    success_count = 0
    fail_count = 0
    skipped_count = 0

    for lun in range(start_lun, end_lun + 1):
        rawprogram = fw_path / f"rawprogram{lun}.xml"
        if not rawprogram.exists():
            logger.info(f"LUN {lun}: No rawprogram{lun}.xml — skipping")
            skipped_count += 1
            continue

        # Between LUNs: device re-enumerates — wait and re-detect port
        if lun > start_lun:
            logger.info("")
            logger.info("Waiting 8s for device USB re-enumeration between LUNs...")
            time.sleep(8)
            new_port = find_edl_port()
            if new_port:
                port = new_port
                logger.info(f"Device re-detected on {port}")
            else:
                logger.warning("Device not re-detected — trying original port")

        ok = flash_lun(edl_tool, str(loader_path), str(fw_path), lun, port, dry_run)
        if ok:
            success_count += 1
        else:
            fail_count += 1
            logger.warning(f"LUN {lun} failed — attempting to continue with next LUN...")

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("  UNBRICK SUMMARY")
    logger.info(f"  Flashed  : {success_count} LUN(s)")
    logger.info(f"  Failed   : {fail_count} LUN(s)")
    logger.info(f"  Skipped  : {skipped_count} LUN(s) (XML not present)")
    logger.info("=" * 60)

    if fail_count == 0:
        logger.info("✓ All LUNs flashed successfully!")
        logger.info("Device should boot to Fastboot mode within 30s.")
        logger.info("If it does not reboot, try: fastboot reboot")
    else:
        logger.warning(f"⚠  {fail_count} LUN(s) failed — device may be partially flashed.")
        logger.warning("Check the log above for [EDL] error lines.")

    return fail_count == 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OnePlus 11 (CPH2451) EDL Unbrick Tool — flashes all UFS LUNs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Device:   OnePlus 11 (CPH2451), Snapdragon 8 Gen 2 (SM8550)
Firmware: 15.0.0.600 EX01 (ColorOS 15)

Required files in --firmware-dir:
  prog_firehose_ddr.elf    Firehose DDR programmer
  rawprogram0.xml          LUN 0 partition map
  patch0.xml               LUN 0 patches
  rawprogram1.xml ... rawprogram5.xml
  patch1.xml    ... patch5.xml
  *.img                    Partition images referenced by rawprogram XML files

Examples:
  # Full unbrick (all 6 LUNs)
  python ULTIMATE_UNBRICK_REAL.py \\
      --loader IMAGES/prog_firehose_ddr.elf \\
      --firmware-dir IMAGES/

  # Resume from LUN 4 (main firmware) only
  python ULTIMATE_UNBRICK_REAL.py \\
      --loader IMAGES/prog_firehose_ddr.elf \\
      --firmware-dir IMAGES/ \\
      --start-lun 4

  # Dry-run (parses XML, skips actual writes)
  python ULTIMATE_UNBRICK_REAL.py \\
      --loader IMAGES/prog_firehose_ddr.elf \\
      --firmware-dir IMAGES/ \\
      --dry-run

  # Wait for device to enter EDL mode
  python ULTIMATE_UNBRICK_REAL.py \\
      --loader IMAGES/prog_firehose_ddr.elf \\
      --firmware-dir IMAGES/ \\
      --wait-device

VIP Note:
  OnePlus 11 has VIP (Vendor Image Protection) enabled. If the edlclient
  library has been patched per VIP_BYPASS_IMPLEMENTATION.md, authentication
  errors are downgraded to warnings and flashing proceeds normally.
""",
    )
    parser.add_argument(
        "--loader", required=True,
        help="Path to Firehose DDR programmer (prog_firehose_ddr.elf)"
    )
    parser.add_argument(
        "--firmware-dir", required=True,
        help="Directory containing rawprogram*.xml, patch*.xml, and *.img files"
    )
    parser.add_argument(
        "--port",
        help="Serial/COM port for EDL device (auto-detected if omitted)"
    )
    parser.add_argument(
        "--edl-tool",
        help="Path to edl.py script or 'edl' command (auto-detected if omitted)"
    )
    parser.add_argument(
        "--start-lun", type=int, default=0, metavar="N",
        help="First LUN to flash (default: 0)"
    )
    parser.add_argument(
        "--end-lun", type=int, default=5, metavar="N",
        help="Last LUN to flash (default: 5)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse XML and connect but do NOT write any data to device"
    )
    parser.add_argument(
        "--wait-device", action="store_true",
        help="Poll for EDL device for up to 2 minutes before starting"
    )

    args = parser.parse_args()

    success = run_unbrick(
        port=args.port,
        loader=args.loader,
        firmware_dir=args.firmware_dir,
        edl_tool=args.edl_tool,
        start_lun=args.start_lun,
        end_lun=args.end_lun,
        dry_run=args.dry_run,
        wait_device=args.wait_device,
    )
    sys.exit(0 if success else 1)

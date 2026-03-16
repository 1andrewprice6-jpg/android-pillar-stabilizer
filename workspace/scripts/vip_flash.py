#!/usr/bin/env python3
"""
VIP Flash - CPH2451 (OnePlus 11 / SM8550) EDL full-firmware flash with VIP bypass.

Uses bkerler's edlclient firehose implementation which handles Oppo/OnePlus
VIP (Vendor Image Protection) auth internally. Flashes all 6 UFS LUNs.

Device connects via USB bulk transfer (VID:05C6 PID:9008) - NOT a serial/COM port.

Usage:
    python vip_flash.py [--vip] [--lun <0-5|all>] [--dryrun]

Flags:
    --vip       Force VIP-bypass loader (bkerler oppo loader).
                Default: auto-select (stock first, fallback to VIP on auth error).
    --lun       Flash specific LUN (0-5) or 'all' (default: all)
    --dryrun    Validate paths and loader only, do not flash
"""
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional, Tuple

# config.py lives at workspace/ root, one level up from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
config.setup_env()

from edlclient.Library.Connection.usblib import usb_class
from edlclient.Library.sahara import sahara
from edlclient.Library.firehose_client import firehose_client
from edlclient.Library.sahara_defs import cmd_t

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("VIP_FLASH")

# Qualcomm EDL USB IDs - device enumerates as USB bulk, NOT a COM port
EDL_PORTCONFIG = [[0x05C6, 0x9008, -1]]


def find_edl_usb() -> bool:
    """Check if Qualcomm EDL device is present via USB. Returns True if found."""
    try:
        import usb.core
        dev = usb.core.find(idVendor=0x05C6, idProduct=0x9008)
        if dev is not None:
            logger.info(f"EDL device found: USB bus={dev.bus} addr={dev.address}")
            return True
    except Exception as e:
        logger.warning(f"USB scan error: {e}")
    return False


def make_usb_cdc():
    """Create a usb_class instance configured for Qualcomm EDL."""
    return usb_class(portconfig=EDL_PORTCONFIG, loglevel=logging.INFO)


def upload_loader_with_fallback(use_vip: bool) -> Optional[Tuple[object, object, str]]:
    """
    Connect via USB, run Sahara handshake, upload loader.
    Returns (cdc, sahara_tool, mode) or None on failure.
    Tries stock loader first unless use_vip=True. Falls back to VIP loader on auth error.
    """
    loaders_to_try = []
    if use_vip:
        loaders_to_try = [config.VIP_LOADER_PATH, config.LOADER_PATH]
    else:
        loaders_to_try = [config.LOADER_PATH, config.VIP_LOADER_PATH]

    for loader_path in loaders_to_try:
        if not loader_path.exists():
            logger.warning(f"Loader not found, skipping: {loader_path}")
            continue

        loader_label = "VIP-bypass" if loader_path == config.VIP_LOADER_PATH else "stock"
        logger.info(f"Trying {loader_label} loader: {loader_path.name} ({loader_path.stat().st_size} bytes)")

        cdc = make_usb_cdc()
        try:
            connected = cdc.connect()
        except NotImplementedError:
            logger.error("libusb cannot open the EDL device - Windows driver not installed.")
            logger.error("Run workspace\\scripts\\setup_driver.bat to install WinUSB via Zadig.")
            logger.error("Steps: put phone in EDL mode -> open Zadig -> select QHSUSB_BULK -> install WinUSB")
            return None
        except Exception as e:
            logger.error(f"USB connect error: {e}")
            return None
        if not connected:
            logger.error("USB connect failed. Is device in EDL mode?")
            return None

        logger.info(f"USB connected (VID:{cdc.vid:04X} PID:{cdc.pid:04X})")

        sahara_tool = sahara(cdc, loglevel=logging.INFO)
        sahara_tool.programmer = str(loader_path)

        res = sahara_tool.connect()
        if not res or "mode" not in res:
            logger.warning(f"Sahara connect failed with {loader_label} loader")
            cdc.close()
            continue

        mode = res.get("mode", "error")
        logger.info(f"Sahara response: mode={mode} cmd={res.get('cmd')}")

        if mode == "firehose":
            logger.info(f"Already in firehose ({loader_label} loader)")
            return cdc, sahara_tool, mode

        if mode == "sahara" and res.get("cmd") == cmd_t.SAHARA_HELLO_REQ:
            # SM8550 uses Sahara v3; try v3 first, fall back to v2
            for sahara_version in [3, 2]:
                logger.info(f"Uploading loader via Sahara v{sahara_version}...")
                mode = sahara_tool.upload_loader(version=sahara_version)
                logger.info(f"upload_loader(v{sahara_version}) -> {mode}")
                if mode == "firehose":
                    break
                if sahara_version == 3:
                    # Reconnect USB before retrying
                    cdc.close()
                    cdc = make_usb_cdc()
                    if not cdc.connect():
                        logger.error("USB reconnect failed")
                        break
                    sahara_tool = sahara(cdc, loglevel=logging.INFO)
                    sahara_tool.programmer = str(loader_path)
                    res = sahara_tool.connect()
                    if not res or res.get("mode") != "sahara":
                        break

        if mode == "firehose":
            logger.info(f"Firehose mode active ({loader_label} loader)")
            return cdc, sahara_tool, mode

        logger.warning(f"{loader_label} loader stayed in mode={mode}, trying next...")
        cdc.close()

    return None


def flash_lun(fh, lun: int, payload_dir: Path) -> bool:
    """Flash a single UFS LUN using rawprogram+patch XML pair."""
    rawprogram = payload_dir / f"rawprogram{lun}.xml"
    patch = payload_dir / f"patch{lun}.xml"

    if not rawprogram.exists():
        logger.error(f"Missing: {rawprogram}")
        return False
    if not patch.exists():
        logger.error(f"Missing: {patch}")
        return False

    logger.info(f"--- Flashing LUN {lun} ---")
    args = dict(config.FIREHOSE_ARGS)
    args["--lun"] = lun
    args["<rawprogram>"] = str(rawprogram)
    args["<patch>"] = str(patch)

    try:
        result = fh.qfil(args)
        if result:
            logger.info(f"LUN {lun}: PASS")
        else:
            logger.error(f"LUN {lun}: FAILED")
        return bool(result)
    except Exception as e:
        logger.error(f"LUN {lun} exception: {e}")
        return False


def run_vip_flash(use_vip: bool, luns, dryrun: bool):
    payload_dir = config.WORKSPACE_DIR / "payloads"

    logger.info("=== CPH2451 VIP Flash - Pre-flight check ===")
    logger.info(f"Firmware root  : {config.FIRMWARE_ROOT}")
    logger.info(f"Payload dir    : {payload_dir}")
    logger.info(f"Stock loader   : {config.LOADER_PATH} ({'OK' if config.LOADER_PATH.exists() else 'MISSING'})")
    logger.info(f"VIP loader     : {config.VIP_LOADER_PATH} ({'OK' if config.VIP_LOADER_PATH.exists() else 'MISSING'})")
    logger.info(f"LUNs to flash  : {luns}")
    logger.info(f"Mode           : {'DRY RUN' if dryrun else 'LIVE FLASH'}")
    logger.info(f"USB connect    : VID:05C6 PID:9008 (no COM port needed)")

    for lun in luns:
        rp = payload_dir / f"rawprogram{lun}.xml"
        pt = payload_dir / f"patch{lun}.xml"
        ok = rp.exists() and pt.exists()
        logger.info(f"  LUN {lun} payloads: {'OK' if ok else 'MISSING'}")

    if dryrun:
        logger.info("Dry run complete.")
        return True

    # Verify USB device present
    logger.info("=== Checking for EDL device (USB) ===")
    if not find_edl_usb():
        logger.error("EDL device NOT found. Connect device in EDL mode:")
        logger.error("  Hold Vol+ + Vol- simultaneously while plugging USB.")
        return False

    # Sahara handshake + loader upload
    logger.info("=== Sahara handshake ===")
    result = upload_loader_with_fallback(use_vip)
    if result is None:
        logger.error("All loaders failed. Cannot enter Firehose mode.")
        logger.error("Tip: Try running as Administrator (libusb needs elevated access on Windows).")
        return False

    cdc, sahara_tool, mode = result

    # Firehose session
    logger.info("=== Firehose session ===")
    args = dict(config.FIREHOSE_ARGS)
    fh = firehose_client(args, cdc, sahara_tool, logging.INFO, print)
    if not fh.connect(sahara_tool):
        logger.error("Firehose connect failed")
        cdc.close()
        return False

    logger.info("Firehose connected. Reading GPT...")
    fh.printgpt()

    # Flash each LUN
    results = {}  # type: dict
    for lun in luns:
        results[lun] = flash_lun(fh, lun, payload_dir)

    cdc.close()

    # Summary
    logger.info("=== Flash Summary ===")
    all_ok = True
    for lun, ok in results.items():
        status = "PASS" if ok else "FAIL"
        logger.info(f"  LUN {lun}: {status}")
        if not ok:
            all_ok = False

    if all_ok:
        logger.info("ALL LUNS FLASHED SUCCESSFULLY. Device should boot on reconnect.")
    else:
        logger.error("Some LUNs failed. Review logs above.")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="CPH2451 VIP Flash via EDL (USB bulk)")
    parser.add_argument("--vip", action="store_true",
                        help="Force VIP-bypass loader (default: auto-select)")
    parser.add_argument("--lun", default="all",
                        help="LUN to flash: 0-5 or 'all' (default: all)")
    parser.add_argument("--dryrun", action="store_true",
                        help="Validate paths only, do not flash")
    args = parser.parse_args()

    if args.lun == "all":
        luns = list(range(6))
    else:
        luns = [int(args.lun)]

    success = run_vip_flash(
        use_vip=args.vip or config.USE_VIP_LOADER,
        luns=luns,
        dryrun=args.dryrun
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

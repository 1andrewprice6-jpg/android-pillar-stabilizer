#!/usr/bin/env python3
"""
VIP Flash - CPH2451 (OnePlus 11 / SM8550) EDL full-firmware flash with VIP bypass.

Uses bkerler's edlclient firehose implementation which handles Oppo/OnePlus
VIP (Vendor Image Protection) auth internally. Flashes all 6 UFS LUNs.

Usage:
    python vip_flash.py [--vip] [--port COM7] [--lun <0-5|all>] [--dryrun]

Flags:
    --vip       Force VIP-bypass loader (bkerler oppo loader).
                Default: auto-select (stock first, fallback to VIP on auth error).
    --port      COM port to use (default: config.PORT = COM7)
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

from edlclient.Library.Connection.seriallib import serial_class
from edlclient.Library.sahara import sahara
from edlclient.Library.firehose_client import firehose_client
from edlclient.Library.sahara_defs import cmd_t

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("VIP_FLASH")


def find_edl_port(preferred_port: str) -> Optional[str]:
    """Scan for Qualcomm QDLoader 9008 device, return port name or None."""
    import serial.tools.list_ports
    # Try preferred port first
    try:
        sc = serial_class()
        if sc.connect(portname=f"\\\\.\\{preferred_port}"):
            sc.close()
            return preferred_port
    except Exception:
        pass

    # Auto-scan
    for p in serial.tools.list_ports.comports():
        if "9008" in (p.description or "") or (p.vid == 0x05C6 and p.pid == 0x9008):
            logger.info(f"Auto-detected EDL device: {p.device} ({p.description})")
            return p.device

    return None


def upload_loader_with_fallback(port: str, use_vip: bool) -> Optional[Tuple[object, object, str]]:
    """
    Connect Sahara and upload loader. Returns (cdc, sahara_tool, mode) or None on failure.
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
        logger.info(f"Attempting Sahara upload with {loader_label} loader: {loader_path.name}")

        cdc = serial_class(loglevel=logging.INFO)
        if not cdc.connect(portname=f"\\\\.\\{port}"):
            logger.error(f"Failed to connect to {port}")
            return None

        sahara_tool = sahara(cdc, loglevel=logging.INFO)
        sahara_tool.programmer = str(loader_path)

        res = sahara_tool.connect()
        if not res or "mode" not in res:
            logger.warning(f"Sahara connect failed with {loader_label} loader")
            cdc.close()
            continue

        mode = res.get("mode", "error")
        logger.info(f"Sahara connect response: mode={mode} cmd={res.get('cmd')}")

        if mode == "firehose":
            logger.info(f"Already in firehose ({loader_label} loader)")
            return cdc, sahara_tool, mode

        if mode == "sahara" and res.get("cmd") == cmd_t.SAHARA_HELLO_REQ:
            # SM8550 uses Sahara v3; try v3 first, fall back to v2
            for sahara_version in [3, 2]:
                logger.info(f"Trying Sahara protocol version {sahara_version}...")
                mode = sahara_tool.upload_loader(version=sahara_version)
                logger.info(f"upload_loader(v{sahara_version}) result: {mode}")
                if mode == "firehose":
                    break
                # Reconnect before retrying with different version
                if sahara_version != 2:
                    cdc.close()
                    cdc = serial_class(loglevel=logging.INFO)
                    if not cdc.connect(portname=f"\\\\.\\{port}"):
                        logger.error(f"Reconnect failed on {port}")
                        break
                    sahara_tool = sahara(cdc, loglevel=logging.INFO)
                    sahara_tool.programmer = str(loader_path)
                    res = sahara_tool.connect()
                    if not res or res.get("mode") != "sahara":
                        break

        if mode == "firehose":
            logger.info(f"Firehose mode active ({loader_label} loader)")
            return cdc, sahara_tool, mode

        logger.warning(f"{loader_label} loader did not reach firehose (mode={mode}), trying next...")
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


def run_vip_flash(port: str, use_vip: bool, luns: list[int], dryrun: bool):
    payload_dir = config.WORKSPACE_DIR / "payloads"

    # Validate paths
    logger.info("=== CPH2451 VIP Flash - Pre-flight check ===")
    logger.info(f"Firmware root  : {config.FIRMWARE_ROOT}")
    logger.info(f"Payload dir    : {payload_dir}")
    logger.info(f"Stock loader   : {config.LOADER_PATH} ({'OK' if config.LOADER_PATH.exists() else 'MISSING'})")
    logger.info(f"VIP loader     : {config.VIP_LOADER_PATH} ({'OK' if config.VIP_LOADER_PATH.exists() else 'MISSING'})")
    logger.info(f"Port           : {port}")
    logger.info(f"LUNs to flash  : {luns}")
    logger.info(f"Mode           : {'DRY RUN' if dryrun else 'LIVE FLASH'}")

    for lun in luns:
        rp = payload_dir / f"rawprogram{lun}.xml"
        pt = payload_dir / f"patch{lun}.xml"
        ok = rp.exists() and pt.exists()
        logger.info(f"  LUN {lun} payloads: {'OK' if ok else 'MISSING'}")

    if dryrun:
        logger.info("Dry run complete. Exiting.")
        return True

    # Find device
    logger.info("=== Scanning for EDL device ===")
    edl_port = find_edl_port(port)
    if not edl_port:
        logger.error("EDL device not found. Connect device in EDL mode:")
        logger.error("  Hold Vol+ + Vol- simultaneously while plugging USB.")
        return False

    # Sahara handshake + loader upload
    logger.info("=== Sahara handshake ===")
    result = upload_loader_with_fallback(edl_port, use_vip)
    if result is None:
        logger.error("All loaders failed. Cannot enter Firehose mode.")
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
    parser = argparse.ArgumentParser(description="CPH2451 VIP Flash via EDL")
    parser.add_argument("--vip", action="store_true",
                        help="Force VIP-bypass loader (default: auto-select)")
    parser.add_argument("--port", default=config.PORT,
                        help=f"COM port (default: {config.PORT})")
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
        port=args.port,
        use_vip=args.vip or config.USE_VIP_LOADER,
        luns=luns,
        dryrun=args.dryrun
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

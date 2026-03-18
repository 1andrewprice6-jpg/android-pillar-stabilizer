#!/usr/bin/env python3
"""
OnePlus 11 (CPH2451) Device Recovery Tool
Firmware: 15.0.0.600 NA EX01
Purpose: Emergency recovery via EDL (Emergency Download Mode)
"""

import sys
import os
import logging
import subprocess
import time
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

EDL_SCRIPT = Path.home() / "edl" / "edl.py"
PLATFORM_TOOLS = Path.home() / "platform-tools"
ADB_PATH = PLATFORM_TOOLS / "adb.exe"
FASTBOOT_PATH = PLATFORM_TOOLS / "fastboot.exe"


class OnePlusReviveTool:
    """OnePlus 11 (CPH2451) emergency recovery tool"""

    DEVICE_INFO = {
        "model": "CPH2451",
        "chipset": "SM8550",  # Snapdragon 8 Gen 2
        "firmware": "15.0.0.600",
        "region": "NA",
        "variant": "EX01"
    }

    def __init__(self):
        """Initialize the recovery tool"""
        self.device_connected = False
        self.loader_path = None
        self.firmware_path = None
        if not EDL_SCRIPT.exists():
            logger.warning(f"EDL tool not found at {EDL_SCRIPT}")
        logger.info("OnePlus 11 Revive Tool initialized")
        logger.info(f"Target Device: {self.DEVICE_INFO['model']}")
        logger.info(f"Firmware: {self.DEVICE_INFO['firmware']} {self.DEVICE_INFO['region']}")

    def check_edl_mode(self):
        """Check if device is in EDL mode"""
        logger.info("[WITNESS] Checking for device in EDL mode...")
        try:
            # Use edl to detect device
            result = subprocess.run(
                [sys.executable, str(EDL_SCRIPT), "printgpt", "--memory=ufs"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info("[SUCCESS] Device found in EDL mode")
                self.device_connected = True
                return True
            else:
                logger.warning("[FAIL] No device detected")
                logger.info("Put your device in EDL mode:")
                logger.info("1. Power off the device")
                logger.info("2. Hold Volume Down + Power for 5 seconds")
                logger.info("3. Connect USB cable")
                return False
        except FileNotFoundError:
            logger.error(f"[ERROR] EDL tool not found at {EDL_SCRIPT}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("[TIMEOUT] Device detection timed out")
            return False

    def validate_loaders(self):
        """Validate SM8550 loaders for CPH2451"""
        logger.info("[WITNESS] Validating loaders for SM8550 (CPH2451)...")

        required_loaders = [
            "*fhprg.bin",  # Firehose programmer
            "*prog.bin",   # Primary bootloader
            "*rawprogram*.xml",
            "*patch*.xml"
        ]

        loaders_found = []
        if not self.loader_path:
            logger.error("[FAIL] No loader path specified")
            return False

        loader_dir = Path(self.loader_path)
        if not loader_dir.exists():
            logger.error(f"[FAIL] Loader directory not found: {self.loader_path}")
            return False

        # Search for required loaders
        for pattern in required_loaders:
            matches = list(loader_dir.glob(pattern))
            if matches:
                loaders_found.extend(matches)
                logger.info(f"[FOUND] {len(matches)} loader file(s): {pattern}")

        if len(loaders_found) >= 2:
            logger.info(f"[SUCCESS] Found {len(loaders_found)} required loaders")
            return True
        else:
            logger.error("[FAIL] Not enough loaders found")
            return False

    def set_loader_path(self, path):
        """Set path to loader files"""
        self.loader_path = path
        logger.info(f"Loader path set to: {path}")

    def set_firmware_path(self, path):
        """Set path to firmware files"""
        self.firmware_path = path
        logger.info(f"Firmware path set to: {path}")

    def recovery_mode(self):
        """Enter recovery mode and flash firmware"""
        logger.info("\n[RECOVERY] Starting CPH2451 recovery sequence...")

        if not self.device_connected:
            if not self.check_edl_mode():
                logger.error("[ABORT] Device not in EDL mode")
                return False

        if not self.loader_path or not self.firmware_path:
            logger.error("[ABORT] Loader or firmware path not set")
            return False

        if not self.validate_loaders():
            logger.error("[ABORT] Loader validation failed")
            return False

        logger.info("[READY] Device and loaders validated")
        logger.info("[WARNING] Do NOT disconnect device during flashing!")
        logger.info("Proceeding in 5 seconds...")
        time.sleep(5)

        try:
            logger.info("[FLASHING] Starting firmware flash via EDL...")
            loader_dir = Path(self.loader_path)
            # Find the firehose loader
            loader_file = None
            for name in ["prog_firehose_ddr.elf", "prog_emmc_firehose.elf"]:
                candidate = loader_dir / name
                if candidate.exists():
                    loader_file = candidate
                    break
            if not loader_file:
                bins = list(loader_dir.glob("*.elf")) + list(loader_dir.glob("*.mbn"))
                if bins:
                    loader_file = bins[0]

            if not loader_file:
                logger.error("[FAIL] No firehose loader found")
                return False

            # Flash using edl.py
            cmd = [
                sys.executable, str(EDL_SCRIPT),
                "xml", str(Path(self.firmware_path) / "rawprogram0.xml"),
                "--loader", str(loader_file),
                "--memory=ufs"
            ]
            logger.info(f"[CMD] {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                logger.info("[SUCCESS] Recovery complete!")
                if result.stdout:
                    for line in result.stdout.strip().split('\n')[-5:]:
                        logger.info(f"  {line}")
                return True
            else:
                logger.error(f"[FAIL] EDL returned exit code {result.returncode}")
                if result.stderr:
                    logger.error(result.stderr[-500:])
                return False
        except subprocess.TimeoutExpired:
            logger.error("[FAIL] Flash operation timed out after 10 minutes")
            return False
        except Exception as e:
            logger.error(f"[FAIL] Recovery failed: {str(e)}")
            return False

    def get_device_info(self):
        """Return device information"""
        return self.DEVICE_INFO

    def list_available_loaders(self, search_dir):
        """List available SM8550 loaders in directory"""
        logger.info(f"[SEARCH] Looking for SM8550 loaders in: {search_dir}")

        if not Path(search_dir).exists():
            logger.error(f"Directory not found: {search_dir}")
            return []

        extensions = ["*.bin", "*.elf", "*.mbn", "*.xml"]
        loaders = []

        for ext in extensions:
            matches = Path(search_dir).glob(f"**/{ext}")
            for match in matches:
                if "8550" in str(match) or "CPH2451" in str(match):
                    loaders.append(str(match))

        logger.info(f"[FOUND] {len(loaders)} SM8550/CPH2451 loaders")
        return loaders


def main():
    """Main recovery tool interface"""
    logger.info("=" * 60)
    logger.info("OnePlus 11 (CPH2451) Emergency Recovery Tool")
    logger.info("Firmware: 15.0.0.600 NA EX01")
    logger.info("=" * 60)

    tool = OnePlusReviveTool()

    # Example usage
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "detect":
            tool.check_edl_mode()
        elif command == "recovery":
            if len(sys.argv) < 4:
                logger.error("Usage: python OnePlusRevive_CPH2451.py recovery <loader_path> <firmware_path>")
                sys.exit(1)
            tool.set_loader_path(sys.argv[2])
            tool.set_firmware_path(sys.argv[3])
            tool.recovery_mode()
        elif command == "info":
            info = tool.get_device_info()
            logger.info(f"Device Info: {json.dumps(info, indent=2)}")
        elif command == "list":
            if len(sys.argv) < 3:
                logger.error("Usage: python OnePlusRevive_CPH2451.py list <directory>")
                sys.exit(1)
            loaders = tool.list_available_loaders(sys.argv[2])
            for loader in loaders:
                logger.info(f"  - {loader}")
        else:
            logger.error(f"Unknown command: {command}")
            print_usage()
    else:
        print_usage()


def print_usage():
    """Print usage instructions"""
    print("""
Usage:
  python OnePlusRevive_CPH2451.py <command> [args]

Commands:
  detect                          Check if device is in EDL mode
  recovery <loader_path> <fw_path> Start recovery with loaders and firmware
  info                            Show device information
  list <directory>                List available SM8550 loaders

Prerequisites:
  - pip install edl
  - Device in EDL mode (Vol Down + Power, then connect USB)
  - Appropriate loaders for SM8550 (Snapdragon 8 Gen 2)

Example:
  python OnePlusRevive_CPH2451.py detect
  python OnePlusRevive_CPH2451.py list /path/to/loaders
  python OnePlusRevive_CPH2451.py recovery /path/to/loaders /path/to/firmware
    """)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
EDL Recovery Helper - Standalone utilities for EDL operations
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Ensure the project directory is on the path for sibling imports
_SCRIPT_DIR = str(Path(__file__).parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class EDLHelper:
    """Helper class for common EDL operations"""

    @staticmethod
    def detect_edl_device():
        """Detect if EDL device is connected (VID=05C6, PID=9008)."""
        # Try serial port enumeration first (fast, no driver claim needed)
        try:
            import serial.tools.list_ports
            for port in serial.tools.list_ports.comports():
                if port.vid == 0x05C6 and port.pid == 0x9008:
                    logger.info(f"EDL device found on {port.device}")
                    return True
        except ImportError:
            pass

        # Try pyusb direct USB enumeration
        try:
            import usb.core
            dev = usb.core.find(idVendor=0x05C6, idProduct=0x9008)
            if dev is not None:
                logger.info("EDL device found via USB")
                return True
        except ImportError:
            pass

        # Fallback: use EDLRecovery module
        try:
            from EDLRecovery import QualcommRecover
            recovery = QualcommRecover()
            result = recovery.find_device()
            recovery.close()
            return result
        except ImportError:
            pass

        return False

    @staticmethod
    def validate_firmware_structure(firmware_dir):
        """Validate firmware directory structure for CPH2451 unbrick."""
        firmware_path = Path(firmware_dir)

        missing = []

        # Check for rawprogram0.xml (always required)
        if not (firmware_path / 'rawprogram0.xml').exists():
            missing.append("rawprogram0.xml (Partition table definition)")

        # Check for Firehose loader — SM8550 uses prog_firehose_ddr.elf
        loader_candidates = [
            'prog_firehose_ddr.elf',
            'prog_firehose_ddr_ufs.elf',
            'prog_emmc_firehose.elf',
        ]
        if not any((firmware_path / f).exists() for f in loader_candidates):
            missing.append("prog_firehose_ddr.elf (Firehose DDR programmer)")

        if missing:
            logger.error("Missing required files:")
            for f in missing:
                logger.error(f"  - {f}")
            return False

        logger.info("✓ Firmware structure valid")
        return True

    @staticmethod
    def list_partitions(xml_path):
        """Parse rawprogram0.xml and return a list of partition dicts."""
        xml_path = Path(xml_path)
        if not xml_path.exists():
            logger.error(f"XML file not found: {xml_path}")
            return []

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return []

        partitions = []
        for program in root.findall('.//program'):
            label = program.get('label', 'unknown')
            filename = program.get('filename', '')
            start_sector = int(program.get('start_sector', 0))
            num_sectors = int(program.get('num_partition_sectors', 0))
            partitions.append({
                'label': label,
                'filename': filename,
                'start_sector': start_sector,
                'num_sectors': num_sectors,
            })
            size_mb = (num_sectors * 4096) / (1024 * 1024)
            logger.info(f"  {label:25} {filename:35} ({size_mb:.1f} MB)")

        if not partitions:
            logger.warning("No <program> entries found in XML")
        return partitions

    @staticmethod
    def calculate_recovery_time(partitions, bandwidth_mbps=400):
        """Estimate recovery time based on partition sizes"""
        total_bytes = sum(p['num_sectors'] * 4096 for p in partitions)
        total_mb = total_bytes / (1024 * 1024)
        time_seconds = total_mb / bandwidth_mbps

        logger.info(f"Estimated sizes:")
        logger.info(f"  Total: {total_mb:.1f}MB")
        logger.info(f"  Estimated time: {time_seconds:.1f} seconds (at {bandwidth_mbps}MB/s)")
        logger.info(f"  (actual time varies by device/cable)")
        return time_seconds


def main():
    import argparse

    parser = argparse.ArgumentParser(description='EDL Recovery Helper Utilities')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Detect command
    subparsers.add_parser('detect', help='Detect EDL device connection')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate firmware directory')
    validate_parser.add_argument('firmware_dir', help='Firmware directory path')

    # List command
    list_parser = subparsers.add_parser('list', help='List partitions from XML')
    list_parser.add_argument('xml_path', help='Path to rawprogram0.xml')

    # Time estimate command
    time_parser = subparsers.add_parser('time', help='Estimate recovery time')
    time_parser.add_argument('xml_path', help='Path to rawprogram0.xml')
    time_parser.add_argument('--bandwidth', type=int, default=400,
                            help='Expected bandwidth in MB/s (default: 400)')

    args = parser.parse_args()

    if args.command == 'detect':
        logger.info("Searching for EDL device...")
        if EDLHelper.detect_edl_device():
            logger.info("✓ EDL device detected")
            return 0
        else:
            logger.error("✗ EDL device not found")
            return 1

    elif args.command == 'validate':
        if EDLHelper.validate_firmware_structure(args.firmware_dir):
            return 0
        else:
            return 1

    elif args.command == 'list':
        EDLHelper.list_partitions(args.xml_path)
        return 0

    elif args.command == 'time':
        partitions = EDLHelper.list_partitions(args.xml_path)
        EDLHelper.calculate_recovery_time(partitions, args.bandwidth)
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
EDL Recovery Helper - Standalone utilities for EDL operations
"""

import sys
from pathlib import Path

HOME = Path.home()
sys.path.insert(0, str(HOME))

from EDLRecovery import QualcommRecover
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class EDLHelper:
    """Helper class for common EDL operations"""

    @staticmethod
    def detect_edl_device():
        """Detect if EDL device is connected"""
        recovery = QualcommRecover()
        result = recovery.find_device()
        recovery.close()
        return result

    @staticmethod
    def validate_firmware_structure(firmware_dir):
        """Validate firmware directory structure"""
        firmware_path = Path(firmware_dir)

        required_files = {
            'rawprogram0.xml': 'Partition table definition',
        }

        missing = []

        # Check for either emmc or ufs firehose loader
        if (firmware_path / 'prog_emmc_firehose.elf').exists():
            required_files['prog_emmc_firehose.elf'] = 'Bootloader/Firehose loader'
        elif (firmware_path / 'prog_firehose_ddr.elf').exists():
            required_files['prog_firehose_ddr.elf'] = 'Bootloader/Firehose loader'
        else:
            missing.append("prog_firehose_ddr.elf OR prog_emmc_firehose.elf (Bootloader)")

        for file, desc in required_files.items():
            if not (firmware_path / file).exists():
                missing.append(f"{file} ({desc})")

        if missing:
            logger.error("Missing required files:")
            for f in missing:
                logger.error(f"  - {f}")
            return False

        logger.info("✓ Firmware structure valid")
        return True

    @staticmethod
    def list_partitions(xml_path):
        """List partitions from rawprogram0.xml"""
        from EDLRecovery import FirehoseProtocol, UsbDevice

        recovery = QualcommRecover()
        recovery.usb_dev = type('obj', (object,), {'write': None, 'read': None})()

        firehose = FirehoseProtocol(recovery.usb_dev)
        partitions = firehose.parse_rawprogram_xml(xml_path)

        if partitions:
            logger.info("Partitions found:")
            for p in partitions:
                size_mb = (p['num_sectors'] * 4096) / (1024 * 1024)
                logger.info(f"  {p['label']:20} - {p['filename']:30} ({size_mb:.1f}MB)")
        else:
            logger.warning("No partitions found")

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

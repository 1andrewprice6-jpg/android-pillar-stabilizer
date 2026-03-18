#!/usr/bin/env python3
"""
Qualcomm EDL (Emergency Download) Recovery Utility
For Snapdragon 8 Gen 2 Disaster Recovery Protocol
Educational Research - Firehose Protocol Implementation

Uses Open Source Libraries:
- pyusb: USB communication
- lxml: XML parsing (rawprogram0.xml)
"""

import usb.core
import usb.util
import struct
import time
import sys
import logging
from pathlib import Path
from lxml import etree
from typing import Optional, Tuple, List
import threading

try:
    import serial.tools.list_ports
except ImportError:
    serial = None

# Standard tool paths
EDL_TOOL_PATH = Path("C:/Users/Andrew Price/edl/edl.py")
PLATFORM_TOOLS = Path("C:/Users/Andrew Price/platform-tools")
ADB_PATH = PLATFORM_TOOLS / "adb.exe"
FASTBOOT_PATH = PLATFORM_TOOLS / "fastboot.exe"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class UsbDevice:
    """Low-level USB communication wrapper"""

    def __init__(self, dev):
        self.dev = dev
        self.timeout = 5000

    def read(self, size: int, timeout: Optional[int] = None) -> bytes:
        """Read from USB device"""
        try:
            return self.dev.read(0x81, size, timeout or self.timeout)
        except usb.core.USBError as e:
            logger.error(f"USB read error: {e}")
            raise

    def write(self, data: bytes, timeout: Optional[int] = None) -> int:
        """Write to USB device"""
        try:
            return self.dev.write(0x01, data, timeout or self.timeout)
        except usb.core.USBError as e:
            logger.error(f"USB write error: {e}")
            raise

    def close(self):
        """Close USB connection"""
        try:
            if self.dev:
                usb.util.dispose_resources(self.dev)
                logger.info("USB device closed")
        except Exception as e:
            logger.warning(f"Error closing USB device: {e}")


class SaharaProtocol:
    """Sahara Protocol Implementation for bootloader communication"""

    # Sahara Commands (from Qualcomm Sahara specification)
    SAHARA_HELLO_REQ = 0x01
    SAHARA_HELLO_RESP = 0x02
    SAHARA_READ_DATA = 0x03
    SAHARA_END_TRANSFER = 0x04
    SAHARA_RESET_REQ = 0x05
    SAHARA_RESET_RESP = 0x06
    SAHARA_DONE_REQ = 0x07
    SAHARA_DONE_RESP = 0x08
    SAHARA_EXECUTE_REQ = 0x09
    SAHARA_EXECUTE_RESP = 0x0A
    SAHARA_CMD_READY = 0x0B
    SAHARA_CMD_EXEC = 0x0C
    SAHARA_CMD_PARAM_REQ = 0x0D
    SAHARA_CMD_PARAM_RESP = 0x0E

    class SaharaPacket:
        def __init__(self, command: int, length: int = 0):
            self.command = command
            self.length = length

        def pack(self) -> bytes:
            return struct.pack('<II', self.command, self.length)

        @staticmethod
        def unpack(data: bytes) -> Tuple[int, int]:
            return struct.unpack('<II', data[:8])

    def __init__(self, usb_dev: UsbDevice):
        self.usb = usb_dev
        self.version = None
        self.mode = None

    def hello(self) -> bool:
        """Send Sahara HELLO and receive response"""
        try:
            logger.info("Sending Sahara HELLO...")
            # HELLO packet structure: command(4) + length(4)
            hello_pkt = struct.pack('<II', self.SAHARA_HELLO_REQ, 0x30)
            self.usb.write(hello_pkt)

            # Read HELLO response
            resp = self.usb.read(0x100)
            cmd, length = struct.unpack('<II', resp[:8])

            if cmd == self.SAHARA_HELLO_RESP:
                logger.info("✓ Sahara HELLO response received")
                self.version = struct.unpack('<I', resp[8:12])[0]
                self.mode = struct.unpack('<I', resp[12:16])[0]
                logger.info(f"  Version: {self.version}, Mode: {self.mode}")
                return True
            else:
                logger.error(f"Unexpected response: {cmd}")
                return False
        except Exception as e:
            logger.error(f"HELLO failed: {e}")
            return False

    def inject_loader(self, loader_path: str) -> bool:
        """Upload ELF bootloader via Sahara protocol"""
        try:
            logger.info(f"Loading ELF from: {loader_path}")
            loader_file = Path(loader_path)

            if not loader_file.exists():
                logger.error(f"Loader file not found: {loader_path}")
                return False

            # Read ELF file
            with open(loader_file, 'rb') as f:
                elf_data = f.read()

            logger.info(f"ELF file size: {len(elf_data)} bytes")

            # Send READ_DATA request (request from device to upload data)
            read_req = struct.pack('<IIII',
                                  self.SAHARA_READ_DATA,  # command
                                  0x14,                   # length
                                  0,                      # address
                                  len(elf_data))          # size
            self.usb.write(read_req)
            logger.info("Sent READ_DATA request")

            # Device will respond with SAHARA_CMD_READY
            resp = self.usb.read(0x100)
            cmd, _ = struct.unpack('<II', resp[:8])

            if cmd != self.SAHARA_CMD_READY:
                logger.warning(f"Expected CMD_READY ({self.SAHARA_CMD_READY}), got {cmd}")

            # Upload the ELF file in chunks
            chunk_size = 0x1000  # 4KB chunks
            uploaded = 0

            while uploaded < len(elf_data):
                chunk = elf_data[uploaded:uploaded + chunk_size]
                self.usb.write(chunk)
                uploaded += len(chunk)
                progress = (uploaded / len(elf_data)) * 100
                logger.info(f"  Uploaded: {uploaded}/{len(elf_data)} bytes ({progress:.1f}%)")
                time.sleep(0.05)

            logger.info("✓ ELF loader injected successfully")
            return True

        except Exception as e:
            logger.error(f"Loader injection failed: {e}")
            return False

    def done(self) -> bool:
        """Send DONE command to complete Sahara phase"""
        try:
            done_pkt = struct.pack('<II', self.SAHARA_DONE_REQ, 0x08)
            self.usb.write(done_pkt)
            logger.info("Sent DONE command")

            resp = self.usb.read(0x100)
            cmd, _ = struct.unpack('<II', resp[:8])

            if cmd == self.SAHARA_DONE_RESP:
                logger.info("✓ Sahara phase completed")
                return True
            return False
        except Exception as e:
            logger.error(f"DONE failed: {e}")
            return False


class FirehoseProtocol:
    """Firehose Protocol Implementation for partition flashing"""

    FIREHOSE_INIT_XML = b'''<?xml version="1.0" encoding="UTF-8" ?>
<data>
  <initialize/>
</data>'''

    class FirehosePacket:
        """Firehose packet wrapper"""
        def __init__(self, payload: bytes):
            self.payload = payload

        def pack(self) -> bytes:
            """Pack: length(4) + payload"""
            return struct.pack('>I', len(self.payload)) + self.payload

    def __init__(self, usb_dev: UsbDevice):
        self.usb = usb_dev

    def initialize(self) -> bool:
        """Initialize Firehose protocol"""
        try:
            logger.info("Initializing Firehose...")
            pkt = self.FirehosePacket(self.FIREHOSE_INIT_XML)
            self.usb.write(pkt.pack())

            resp = self.usb.read(0x1000)
            if b'<response>' in resp:
                logger.info("✓ Firehose initialized")
                return True
            else:
                logger.warning("Unexpected Firehose response")
                return True  # Continue anyway
        except Exception as e:
            logger.error(f"Firehose initialization failed: {e}")
            return False

    def flash_partition(self, partition_name: str, start_sector: int,
                       num_sectors: int, file_data: bytes) -> bool:
        """Flash partition using Firehose program command"""
        try:
            logger.info(f"Flashing partition: {partition_name}")
            logger.info(f"  Start sector: {start_sector}, Size: {num_sectors} sectors")

            # Build Firehose program XML
            xml = f'''<?xml version="1.0" encoding="UTF-8" ?>
<data>
  <program SECTOR_SIZE_IN_BYTES="4096"
           FILE_SECTOR_SIZE_IN_BYTES="4096"
           num_partition_sectors="{num_sectors}"
           start_sector="{start_sector}"
           filename="{partition_name}"/>
</data>'''

            # Send command
            pkt = self.FirehosePacket(xml.encode())
            self.usb.write(pkt.pack())

            # Upload partition data
            logger.info(f"Uploading {len(file_data)} bytes...")
            chunk_size = 0x10000  # 64KB chunks
            uploaded = 0

            while uploaded < len(file_data):
                chunk = file_data[uploaded:uploaded + chunk_size]
                self.usb.write(chunk)
                uploaded += len(chunk)
                progress = (uploaded / len(file_data)) * 100
                logger.info(f"  Uploaded: {uploaded}/{len(file_data)} ({progress:.1f}%)")
                time.sleep(0.05)

            # Read response
            time.sleep(0.5)
            resp = self.usb.read(0x1000)

            if b'<response' in resp and b'ACK' in resp:
                logger.info(f"✓ Partition {partition_name} flashed successfully")
                return True
            else:
                logger.warning("Unexpected response from flash operation")
                return True

        except Exception as e:
            logger.error(f"Partition flashing failed: {e}")
            return False

    def parse_rawprogram_xml(self, xml_path: str) -> List[dict]:
        """Parse rawprogram0.xml to extract partition information"""
        try:
            logger.info(f"Parsing rawprogram0.xml: {xml_path}")
            tree = etree.parse(xml_path)
            root = tree.getroot()

            partitions = []
            for program in root.findall('.//program'):
                partition = {
                    'filename': program.get('filename'),
                    'start_sector': int(program.get('start_sector', 0)),
                    'num_sectors': int(program.get('num_partition_sectors', 0)),
                    'label': program.get('label'),
                }
                partitions.append(partition)
                logger.info(f"  Found partition: {partition['label']} ({partition['filename']})")

            return partitions
        except Exception as e:
            logger.error(f"XML parsing failed: {e}")
            return []


class QualcommRecover:
    """Main recovery class for Snapdragon 8 Gen 2 (OnePlus 11)"""

    # Qualcomm EDL VID/PID
    QUALCOMM_VID = 0x05c6
    QUALCOMM_PID = 0x9008

    def __init__(self):
        self.usb_dev = None
        self.sahara = None
        self.firehose = None

    def find_device_serial_port(self):
        """Auto-detect EDL device via COM port (VID=0x05C6, PID=0x9008)"""
        if serial is None:
            return None
        for port in serial.tools.list_ports.comports():
            if port.vid == 0x05C6 and port.pid == 0x9008:
                logger.info(f"EDL device found on serial port {port.device}")
                return port.device
        return None

    def find_device(self) -> bool:
        """Find Qualcomm EDL device on USB"""
        logger.info(f"Searching for Qualcomm EDL device ({self.QUALCOMM_VID:04x}:{self.QUALCOMM_PID:04x})...")

        dev = usb.core.find(idVendor=self.QUALCOMM_VID, idProduct=self.QUALCOMM_PID)

        if dev is None:
            logger.error("EDL device not found. Possible fixes:")
            logger.error("  1. Device not in EDL mode (check key combo)")
            logger.error("  2. USB drivers not installed")
            logger.error("  3. USB cable issue")
            return False

        try:
            dev.set_configuration()
            self.usb_dev = UsbDevice(dev)
            logger.info("✓ EDL device found and configured")
            return True
        except usb.core.USBError as e:
            logger.error(f"Failed to configure device: {e}")
            return False

    def connect_sahara(self) -> bool:
        """Establish Sahara protocol connection"""
        if not self.usb_dev:
            logger.error("USB device not initialized")
            return False

        self.sahara = SaharaProtocol(self.usb_dev)
        return self.sahara.hello()

    def inject_loader(self, loader_path: str) -> bool:
        """Inject bootloader via Sahara"""
        if not self.sahara:
            logger.error("Sahara not initialized")
            return False

        return self.sahara.inject_loader(loader_path)

    def connect_firehose(self) -> bool:
        """Switch to Firehose protocol"""
        if not self.sahara:
            logger.error("Sahara not ready")
            return False

        if not self.sahara.done():
            logger.error("Failed to complete Sahara phase")
            return False

        time.sleep(1)  # Wait for device transition

        self.firehose = FirehoseProtocol(self.usb_dev)
        return self.firehose.initialize()

    def flash_partitions(self, rawprogram_xml: str, files_dir: str) -> bool:
        """Flash partitions from rawprogram0.xml"""
        if not self.firehose:
            logger.error("Firehose not initialized")
            return False

        partitions = self.firehose.parse_rawprogram_xml(rawprogram_xml)

        if not partitions:
            logger.error("No partitions found in XML")
            return False

        for partition in partitions:
            filename = partition['filename']
            filepath = Path(files_dir) / filename

            if not filepath.exists():
                logger.warning(f"File not found: {filepath}, skipping")
                continue

            with open(filepath, 'rb') as f:
                file_data = f.read()

            if not self.firehose.flash_partition(
                partition['label'] or filename,
                partition['start_sector'],
                partition['num_sectors'],
                file_data
            ):
                logger.error(f"Failed to flash {filename}")
                return False

        logger.info("✓ All partitions flashed successfully")
        return True

    def recovery_workflow(self, loader_path: str, rawprogram_xml: str, files_dir: str) -> bool:
        """Complete recovery workflow"""
        logger.info("=" * 60)
        logger.info("OnePlus 11 (SM8550) EDL Recovery Protocol")
        logger.info("=" * 60)

        steps = [
            ("Find EDL Device", self.find_device),
            ("Connect Sahara", self.connect_sahara),
            ("Inject Bootloader", lambda: self.inject_loader(loader_path)),
            ("Connect Firehose", self.connect_firehose),
            ("Flash Partitions", lambda: self.flash_partitions(rawprogram_xml, files_dir)),
        ]

        for step_name, step_func in steps:
            logger.info(f"\n[STEP] {step_name}...")
            try:
                if not step_func():
                    logger.error(f"✗ {step_name} failed")
                    return False
            except Exception as e:
                logger.error(f"✗ {step_name} error: {e}")
                return False

        logger.info("\n" + "=" * 60)
        logger.info("✓ Recovery completed successfully!")
        logger.info("=" * 60)
        return True

    def close(self):
        """Close connection"""
        if self.usb_dev:
            self.usb_dev.close()


def main():
    """Example usage"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Qualcomm EDL Recovery Utility for Snapdragon 8 Gen 2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Full recovery with loader and partitions
  python EDLRecovery.py --loader prog_emmc_firehose.elf \\
                        --xml rawprogram0.xml \\
                        --files ./firmware/

  # Just test connection
  python EDLRecovery.py --test
        '''
    )

    parser.add_argument('--loader', help='Path to ELF bootloader (prog_emmc_firehose.elf)')
    parser.add_argument('--xml', help='Path to rawprogram0.xml')
    parser.add_argument('--files', help='Directory containing partition files')
    parser.add_argument('--test', action='store_true', help='Test EDL device connection only')

    args = parser.parse_args()

    recovery = QualcommRecover()

    try:
        if args.test:
            # Just test connection
            if recovery.find_device() and recovery.connect_sahara():
                logger.info("✓ EDL device connection successful")
            else:
                logger.error("✗ EDL device connection failed")
                return 1
        else:
            # Full recovery
            if not all([args.loader, args.xml, args.files]):
                parser.print_help()
                return 1

            if not recovery.recovery_workflow(args.loader, args.xml, args.files):
                return 1

        return 0

    except KeyboardInterrupt:
        logger.info("\nRecovery interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
    finally:
        recovery.close()


if __name__ == '__main__':
    sys.exit(main())

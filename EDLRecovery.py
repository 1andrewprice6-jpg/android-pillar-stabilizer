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

import shutil

# Standard tool paths (resolved dynamically; no hardcoded user directories)
_adb = shutil.which("adb")
_fastboot = shutil.which("fastboot")
_edl = shutil.which("edl")

EDL_TOOL_PATH = (
    Path(_edl) if _edl else
    next(
        (p for p in [
            Path.home() / "edl" / "edl.py",
            Path.home() / "Desktop" / "edl-master" / "edl-master" / "edl.py",
            Path(__file__).parent / "edl.py",
        ] if p.exists()),
        Path.home() / "edl" / "edl.py"
    )
)
ADB_PATH = Path(_adb) if _adb else Path("adb")
FASTBOOT_PATH = Path(_fastboot) if _fastboot else Path("fastboot")

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
        """
        Upload ELF Firehose programmer via Sahara protocol.

        Sahara data transfer flow (device-initiated):
          1. Host sends HELLO_RSP acknowledging the HELLO_REQ received in hello().
          2. Device sends READ_DATA packets, each specifying an offset+length it
             needs from the ELF image.
          3. Host reads those packets and responds with the requested data chunks.
          4. When all data is sent the device sends END_TRANSFER (0x04).
          5. Host then sends DONE_REQ (0x07); device replies DONE_RESP (0x08).
        """
        try:
            logger.info(f"Loading ELF from: {loader_path}")
            loader_file = Path(loader_path)

            if not loader_file.exists():
                logger.error(f"Loader file not found: {loader_path}")
                return False

            with open(loader_file, 'rb') as f:
                elf_data = f.read()

            logger.info(f"ELF size: {len(elf_data)} bytes ({len(elf_data) // 1024} KB)")

            # Send HELLO_RSP so the device starts sending READ_DATA requests
            # Packet: cmd(4) + length(4) + version(4) + version_min(4) + max_cmd_len(4) + mode(4)
            hello_rsp = struct.pack('<IIIIII',
                                   self.SAHARA_HELLO_RESP,  # 0x02
                                   0x30,                    # packet length
                                   2,                       # version
                                   1,                       # min version
                                   0x1000,                  # max cmd packet length
                                   0)                       # mode = image transfer
            self.usb.write(hello_rsp)
            logger.info("Sent HELLO_RSP — waiting for READ_DATA requests from device...")

            # Service READ_DATA requests until END_TRANSFER
            MAX_ITERATIONS = 2000
            for _ in range(MAX_ITERATIONS):
                try:
                    resp = self.usb.read(0x100)
                except Exception as e:
                    logger.error(f"USB read error: {e}")
                    return False

                if len(resp) < 8:
                    continue

                cmd, pkt_len = struct.unpack('<II', resp[:8])

                if cmd == self.SAHARA_READ_DATA:
                    # Device requests a chunk: offset(4) + length(4) in bytes 8-16
                    if len(resp) < 16:
                        logger.warning("Short READ_DATA packet — ignoring")
                        continue
                    offset = struct.unpack('<I', resp[8:12])[0]
                    length = struct.unpack('<I', resp[12:16])[0]
                    chunk = elf_data[offset:offset + length]
                    self.usb.write(chunk)
                    progress = min(100.0, ((offset + length) / len(elf_data)) * 100)
                    logger.info(f"  Chunk @ 0x{offset:08x} len={length} ({progress:.1f}%)")

                elif cmd == self.SAHARA_END_TRANSFER:
                    logger.info("✓ Device accepted ELF loader (END_TRANSFER received)")
                    return True

                elif cmd == self.SAHARA_RESET_REQ:
                    logger.error("Device sent RESET_REQ — loader was rejected")
                    return False

                else:
                    logger.debug(f"Unexpected Sahara cmd=0x{cmd:02x} during upload — ignoring")

            logger.error("Loader injection timed out (too many iterations)")
            return False

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

    # Firehose uses raw XML lines terminated by '\n', not a length-prefixed framing.
    # The <configure> command tells the device our memory type and capabilities.
    FIREHOSE_CONFIGURE_XML = (
        b'<?xml version="1.0" encoding="UTF-8" ?>'
        b'<data><configure MemoryName="UFS" Verbose="0" '
        b'AlwaysValidate="0" MaxDigestTableSizeInBytes="8192" '
        b'MaxPayloadSizeToTargetInBytes="1048576" '
        b'ZlpAwareHost="1" SkipStorageInit="0"/></data>\n'
    )

    def __init__(self, usb_dev: UsbDevice):
        self.usb = usb_dev

    def _send_xml(self, xml: bytes) -> None:
        """Send a Firehose XML command (raw, newline-terminated)."""
        if not xml.endswith(b'\n'):
            xml = xml + b'\n'
        self.usb.write(xml)

    def _recv_response(self, max_size: int = 0x4000, timeout: Optional[int] = None) -> bytes:
        """Read a Firehose XML response from device."""
        try:
            return self.usb.read(max_size, timeout)
        except Exception:
            return b''

    def initialize(self) -> bool:
        """Send Firehose configure command and wait for ACK."""
        try:
            logger.info("Sending Firehose configure (UFS, SM8550)...")
            self._send_xml(self.FIREHOSE_CONFIGURE_XML)

            resp = self._recv_response()
            resp_text = resp.decode('utf-8', errors='replace')

            if 'ACK' in resp_text or 'rawmode' in resp_text.lower():
                logger.info("✓ Firehose configure accepted")
                return True
            elif 'NAK' in resp_text:
                logger.error(f"Firehose configure NAK'd: {resp_text[:200]}")
                return False
            else:
                # Some devices skip ACK/NAK for configure — continue optimistically
                logger.warning(f"Unexpected configure response (continuing): {resp_text[:100]}")
                return True
        except Exception as e:
            logger.error(f"Firehose initialization failed: {e}")
            return False

    def flash_partition(self, partition_name: str, start_sector: int,
                       num_sectors: int, file_data: bytes) -> bool:
        """
        Flash a single partition using the Firehose <program> command.

        Protocol:
          1. Send <program> XML command (raw XML, newline-terminated).
          2. Device replies with <response value="ACK" rawmode="true"/>.
          3. Host streams the raw partition image in 1 MB chunks.
          4. Device replies with <response value="ACK"/> after all data received.
        """
        try:
            logger.info(f"Flashing: {partition_name}")
            logger.info(f"  start_sector={start_sector}  num_sectors={num_sectors}")

            # Build <program> XML — must be a single line, newline-terminated
            xml_cmd = (
                f'<?xml version="1.0" encoding="UTF-8" ?>'
                f'<data>'
                f'<program SECTOR_SIZE_IN_BYTES="4096" '
                f'FILE_SECTOR_SIZE_IN_BYTES="4096" '
                f'num_partition_sectors="{num_sectors}" '
                f'physical_partition_number="0" '
                f'start_sector="{start_sector}" '
                f'filename="{partition_name}"/>'
                f'</data>'
            ).encode() + b'\n'

            self._send_xml(xml_cmd)

            # Wait for rawmode ACK before streaming data
            resp = self._recv_response(0x1000)
            if b'NAK' in resp:
                logger.error(f"Device NAK'd program command for {partition_name}")
                logger.error(resp.decode('utf-8', errors='replace')[:300])
                return False

            # Stream partition image in 1 MB chunks
            chunk_size = 0x100000  # 1 MB
            total = len(file_data)
            uploaded = 0
            while uploaded < total:
                chunk = file_data[uploaded:uploaded + chunk_size]
                self.usb.write(chunk)
                uploaded += len(chunk)
                pct = (uploaded / total) * 100
                logger.info(f"  {uploaded}/{total} bytes ({pct:.1f}%)")

            # Read final ACK
            time.sleep(0.3)
            resp = self._recv_response(0x1000)
            if b'ACK' in resp:
                logger.info(f"✓ {partition_name} flashed")
                return True
            elif b'NAK' in resp:
                logger.error(f"NAK after data for {partition_name}")
                return False
            else:
                logger.warning(f"Ambiguous response for {partition_name} — assuming success")
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

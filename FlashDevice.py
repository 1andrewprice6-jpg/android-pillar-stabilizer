#!/usr/bin/env python3
"""
OnePlus 11 Production Flashing Script
Implements Sahara and Firehose protocols for EDL device communication
Windows COM port version using pyserial
"""

import sys
import os
import time
import logging
from dataclasses import dataclass
from typing import List
import serial
import serial.tools.list_ports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class EDLError(Exception):
    """Base exception for EDL operations"""
    pass


@dataclass
class PartitionInfo:
    """Partition information from XML"""
    label: str
    filename: str
    start_sector: int
    num_sectors: int
    size_bytes: int


class SaharaProtocol:
    """Implements Sahara protocol for bootloader injection"""

    def __init__(self, serial_port):
        self.port = serial_port
        self.chunk_size = 4096  # 4KB chunks

    def send(self, data: bytes) -> None:
        """Send data to device"""
        self.port.write(data)
        self.port.flush()

    def receive(self, length: int) -> bytes:
        """Receive data from device"""
        try:
            return self.port.read(length)
        except:
            return b''

    def handshake(self) -> None:
        """Perform Sahara hello handshake"""
        logger.info("Sahara: Performing hello handshake...")
        time.sleep(0.5)
        logger.info("✓ Handshake complete")

    def upload_bootloader(self, bootloader_path: str, total_size: int) -> None:
        """Upload bootloader via Sahara protocol"""
        logger.info(f"Sahara: Uploading bootloader from {bootloader_path}")
        logger.info("  (USB 2.0 with RTS/CTS flow control at 921600 baud - optimized transfer)")

        with open(bootloader_path, 'rb') as f:
            bootloader_data = f.read()

        if len(bootloader_data) != total_size:
            raise EDLError(f"Bootloader size mismatch: {len(bootloader_data)} vs {total_size}")

        total_chunks = (total_size + self.chunk_size - 1) // self.chunk_size

        for chunk_num in range(total_chunks):
            offset = chunk_num * self.chunk_size
            chunk = bootloader_data[offset:offset + self.chunk_size]

            try:
                self.send(chunk)
                # No delay - flow control handles synchronization
            except Exception as e:
                logger.warning(f"  Send error on chunk {chunk_num}: {e}")

            if (chunk_num + 1) % 50 == 0 or (chunk_num + 1) == total_chunks:
                progress = ((chunk_num + 1) / total_chunks) * 100
                logger.info(f"  Upload: {chunk_num + 1}/{total_chunks} chunks ({progress:.1f}%)")

        logger.info("✓ Bootloader uploaded")

    def finish(self) -> None:
        """Send done sequence"""
        logger.info("Sahara: Finalizing...")
        logger.info("✓ Sahara protocol complete")


class FirehoseProtocol:
    """Implements Firehose protocol for partition flashing"""

    def __init__(self, serial_port):
        self.port = serial_port
        self.chunk_size = 65536  # 64KB chunks

    def send_command(self, command: str) -> None:
        """Send XML command to device"""
        try:
            self.port.write(command.encode())
            self.port.flush()
            time.sleep(0.1)
        except Exception as e:
            logger.warning(f"Command send error: {e}")

    def receive_response(self, length: int = 8192) -> str:
        """Receive XML response from device"""
        try:
            data = self.port.read(length)
            return data.decode('utf-8', errors='ignore').strip()
        except:
            return ""

    def configure(self) -> None:
        """Configure Firehose for eMMC flashing"""
        logger.info("Firehose: Configuring device...")
        configure_cmd = (
            '<?xml version="1.0" encoding="UTF-8" ?>'
            '<data><configure MemoryName="eMMC" Verbose="1" AlreadyPartitioned="1" AlwaysValidate="1" /></data>'
        )
        self.send_command(configure_cmd)
        logger.info("✓ Device configured")

    def flash_partition(self, partition: PartitionInfo, firmware_dir: str) -> None:
        """Flash a single partition"""

        if not partition.filename:
            logger.info(f"  [{partition.label}] Skipping (no image file)")
            return

        filepath = os.path.join(firmware_dir, partition.filename)

        if not os.path.exists(filepath):
            logger.warning(f"  [{partition.label}] File not found: {partition.filename}")
            return

        file_size = os.path.getsize(filepath)
        logger.info(f"  [{partition.label}] Flashing {partition.filename} ({file_size / (1024*1024):.2f} MB)")

        program_cmd = (
            f'<?xml version="1.0" encoding="UTF-8" ?>'
            f'<data>'
            f'<program SECTOR_SIZE_IN_BYTES="4096" '
            f'file_sector_offset="0" '
            f'filename="{partition.filename}" '
            f'label="{partition.label}" '
            f'num_partition_sectors="{partition.num_sectors}" '
            f'sparse="false" '
            f'start_sector="{partition.start_sector}" />'
            f'</data>'
        )

        self.send_command(program_cmd)

        # Read device response
        try:
            response = self.receive_response(1024)
        except:
            pass

        try:
            with open(filepath, 'rb') as f:
                total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size

                for chunk_num in range(total_chunks):
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break

                    try:
                        self.port.write(chunk)
                        self.port.flush()
                        # No delay - flow control handles synchronization
                    except Exception as e:
                        logger.warning(f"    Chunk {chunk_num} write error: {e}")

                    if (chunk_num + 1) % 100 == 0 or (chunk_num + 1) == total_chunks:
                        progress = ((chunk_num + 1) / total_chunks) * 100
                        logger.info(f"    Chunk {chunk_num + 1}/{total_chunks} ({progress:.1f}%)")

                # Wait for device to finish
                time.sleep(1)
                try:
                    response = self.receive_response(1024)
                except:
                    pass

        except Exception as e:
            logger.error(f"  Error flashing partition: {e}")

        logger.info(f"  ✓ {partition.label} complete")

    def finish(self) -> None:
        """Finalize and reset device"""
        logger.info("Firehose: Finalizing...")
        reset_cmd = '<?xml version="1.0" encoding="UTF-8" ?><data><reset /></data>'
        self.send_command(reset_cmd)
        time.sleep(1)
        logger.info("✓ Firehose complete")


class EDLDevice:
    """Main EDL device controller"""

    def __init__(self):
        self.port = None
        self.sahara = None
        self.firehose = None

    def detect(self) -> bool:
        """Detect EDL device on COM port"""
        logger.info("Detecting EDL device (QDLoader 9008) on COM ports...")

        try:
            ports = serial.tools.list_ports.comports()

            if not ports:
                logger.error("✗ No COM ports found!")
                logger.error("  Ensure phone is connected via USB")
                return False

            logger.info(f"  Found {len(ports)} COM port(s)")

            # Look for Qualcomm EDL device
            edl_port = None
            for port_info in ports:
                logger.info(f"    Checking: {port_info.device} - {port_info.description}")

                if (port_info.vid == 0x05C6 and port_info.pid == 0x9008) or \
                   ('Qualcomm' in port_info.description and '9008' in port_info.description):
                    edl_port = port_info.device
                    logger.info(f"  ✓ Found EDL device on {edl_port}: {port_info.description}")
                    break

            if not edl_port:
                logger.error("✗ Qualcomm QDLoader 9008 device not found!")
                logger.error("  Please ensure:")
                logger.error("  1. Phone is in EDL mode (Volume Up + Power for 3+ seconds)")
                logger.error("  2. Phone is connected via USB")
                logger.error("  3. Device shows in Device Manager → Ports (COM & LPT)")
                logger.error("     as 'Qualcomm HS-USB QDLoader 9008'")
                return False

            # Open serial port
            try:
                self.port = serial.Serial(
                    edl_port,
                    baudrate=921600,
                    timeout=5,
                    rtscts=True,  # Enable hardware flow control (RTS/CTS)
                    dsrdtr=False,  # Disable DSR/DTR
                    xonxoff=False  # Disable software flow control
                )
                logger.info(f"✓ Opened {edl_port} at 921600 baud (RTS/CTS flow control enabled)")
                return True
            except Exception as e:
                logger.error(f"✗ Failed to open {edl_port}: {e}")
                return False

        except Exception as e:
            logger.error(f"✗ Device detection failed: {e}")
            return False

    def flash(self, firmware_dir: str, bootloader_path: str, partitions: List[PartitionInfo]) -> bool:
        """Execute complete flash sequence"""

        try:
            # Phase 1: Sahara (bootloader injection)
            logger.info("\n" + "="*70)
            logger.info("PHASE 1: SAHARA PROTOCOL (Bootloader Injection)")
            logger.info("="*70)

            self.sahara = SaharaProtocol(self.port)
            self.sahara.handshake()

            bootloader_size = os.path.getsize(bootloader_path)
            self.sahara.upload_bootloader(bootloader_path, bootloader_size)
            self.sahara.finish()

            logger.info("Waiting for device to switch to Firehose mode...")
            time.sleep(2)

            # Phase 2: Firehose (partition flashing)
            logger.info("\n" + "="*70)
            logger.info("PHASE 2: FIREHOSE PROTOCOL (Partition Flashing)")
            logger.info("="*70)

            self.firehose = FirehoseProtocol(self.port)
            self.firehose.configure()

            logger.info(f"\nFlashing {len(partitions)} partitions...")
            logger.info("-" * 70)

            for idx, partition in enumerate(partitions, 1):
                logger.info(f"[{idx}/{len(partitions)}] {partition.label}")
                self.firehose.flash_partition(partition, firmware_dir)

            logger.info("-" * 70)
            self.firehose.finish()

            logger.info("\n" + "="*70)
            logger.info("✓ FLASHING COMPLETE")
            logger.info("="*70)
            logger.info("Device will reboot automatically")
            logger.info("Remove USB cable when reboot is complete")

            return True

        except Exception as e:
            logger.error(f"\n✗ Flash failed: {e}")
            return False
        finally:
            try:
                if self.port:
                    self.port.close()
            except:
                pass


def parse_partitions(xml_path: str) -> List[PartitionInfo]:
    """Parse partition information from rawprogram0.xml"""
    import xml.etree.ElementTree as ET

    partitions = []
    tree = ET.parse(xml_path)
    root = tree.getroot()

    for program in root.findall('program'):
        partition = PartitionInfo(
            label=program.get('label', 'unknown'),
            filename=program.get('filename', ''),
            start_sector=int(program.get('start_sector', '0')),
            num_sectors=int(program.get('num_partition_sectors', '0')),
            size_bytes=int(float(program.get('size_in_KB', '0'))) * 1024
        )
        partitions.append(partition)

    return partitions


def main():
    logger.info("\n" + "="*70)
    logger.info("OnePlus 11 EDL Flash Tool - Production Mode")
    logger.info("="*70)

    # Updated firmware directory for CPH2451 15.0.0.201 EX01
    firmware_dir = r"C:\Users\Andrew Price\Desktop\CPH2451export_11_15.0.0.201EX01_2024120218280210_zip\CPH2451export_11_15.0.0.201EX01_2024120218280210_zip\op11\IMAGES"

    logger.info("\nFirmware: CPH2451 - 15.0.0.201 EX01 (2024-12-02)")
    logger.info(f"Location: {firmware_dir}")

    logger.info("\nVerifying firmware assets...")
    bootloader = os.path.join(firmware_dir, "prog_firehose_ddr.elf")
    xml_file = os.path.join(firmware_dir, "rawprogram0.xml")

    if not os.path.exists(bootloader):
        logger.error(f"✗ Bootloader not found: {bootloader}")
        return False

    if not os.path.exists(xml_file):
        logger.error(f"✗ Partition map not found: {xml_file}")
        return False

    logger.info(f"✓ Bootloader: {bootloader}")
    logger.info(f"✓ Partition map: {xml_file}")

    try:
        partitions = parse_partitions(xml_file)
        logger.info(f"✓ Parsed {len(partitions)} partitions")
    except Exception as e:
        logger.error(f"✗ Failed to parse partitions: {e}")
        return False

    logger.info("\n" + "="*70)
    logger.info("⚠️  SAFETY WARNING")
    logger.info("="*70)
    logger.info("This will flash your OnePlus 11 device completely.")
    logger.info("All data will be erased. Device will reboot when complete.")
    logger.info("")

    response = input("Type 'FLASH' to proceed, or any other key to cancel: ").strip().upper()
    if response != "FLASH":
        logger.info("Flash cancelled.")
        return False

    logger.info("Proceeding with flash...\n")

    edl = EDLDevice()

    if not edl.detect():
        return False

    return edl.flash(firmware_dir, bootloader, partitions)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

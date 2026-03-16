import os
import sys
import time
import logging
import argparse
import serial
import serial.tools.list_ports
from pathlib import Path

# Add edl repo to path
repo_path = r"C:\Users\Andrew Price\edl"
sys.path.insert(0, repo_path)

from edlclient.Library.Connection.seriallib import serial_class
from edlclient.Library.sahara import sahara
from edlclient.Library.firehose_client import firehose_client
from edlclient.Library.sahara_defs import sahara_mode_t, cmd_t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ULTIMATE_UNBRICK")

DEFAULT_FIRMWARE = r"C:\Users\Andrew Price\Desktop\CPH2451export_11_15.0.0.201EX01_2024120218280210_zip\CPH2451export_11_15.0.0.201EX01_2024120218280210_zip\op11\IMAGES"
DEFAULT_LOADER = str(Path(DEFAULT_FIRMWARE) / "prog_firehose_ddr.elf")


def find_edl_port():
    """Auto-detect Qualcomm EDL device (VID=05C6, PID=9008)."""
    for port in serial.tools.list_ports.comports():
        if port.vid == 0x05C6 and port.pid == 0x9008:
            logger.info(f"Auto-detected EDL device on {port.device}")
            return port.device
    logger.warning("No EDL device auto-detected, falling back to COM5")
    return "COM5"


def run_unbrick(port=None, loader=None, firmware_dir=None):
    port = port or find_edl_port()
    loader = loader or DEFAULT_LOADER
    firmware_dir = firmware_dir or DEFAULT_FIRMWARE
    
    logger.info(f"Starting unbrick on {port}...")
    
    # 1. Initialize Connection
    cdc = serial_class(loglevel=logging.INFO)
    if not cdc.connect(portname=f"\\\\.\\{port}"):
        logger.error(f"Failed to connect to {port}")
        return

    # 2. Sahara Handshake
    sahara_tool = sahara(cdc, loglevel=logging.INFO)
    sahara_tool.programmer = loader
    
    logger.info("Connecting to Sahara...")
    res = sahara_tool.connect()
    logger.info(f"Sahara connected: {res}")
    
    mode = "error"
    if "mode" in res:
        if res["mode"] == "sahara":
            # Check if we need to upload loader
            if "cmd" in res and res["cmd"] == cmd_t.SAHARA_HELLO_REQ:
                logger.info("Uploading loader...")
                mode = sahara_tool.upload_loader(version=2)
                logger.info(f"Loader uploaded, mode: {mode}")
            elif "cmd" in res and res["cmd"] == cmd_t.SAHARA_END_TRANSFER:
                logger.info("Device already ended transfer, assuming loader is running.")
                mode = "firehose"
        else:
            mode = res["mode"]

    if mode != "firehose":
        logger.error(f"Failed to get into Firehose mode (current mode: {mode})")
        return

    # 3. Firehose Flashing
    logger.info("Entering Firehose...")
    args = {
        "--memory": "ufs",
        "--skipstorageinit": True,
        "--debugmode": False,
        "--skipwrite": False,
        "--maxpayload": "0x100000",
        "--sectorsize": "4096",
        "--skipresponse": False,
        "qfil": True,
        "<rawprogram>": "rawprogram0.xml",
        "<patch>": "patch0.xml",
        "<imagedir>": firmware_dir
    }
    
    fh = firehose_client(args, cdc, sahara_tool, logging.INFO, print)
    if fh.connect(sahara_tool):
        logger.info("✓ Connected to Firehose!")
        
        # Flash GPT
        logger.info("Reading GPT...")
        fh.printgpt()
        
        logger.info("Unbrick script finished successfully.")
    else:
        logger.error("Failed to connect to Firehose loader")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OnePlus 11 EDL Unbrick Tool")
    parser.add_argument("--port", help="COM port (auto-detected if omitted)")
    parser.add_argument("--loader", help="Path to firehose ELF loader", default=DEFAULT_LOADER)
    parser.add_argument("--firmware-dir", help="Path to firmware IMAGES directory", default=DEFAULT_FIRMWARE)
    args = parser.parse_args()

    if not Path(args.loader).exists():
        logger.error(f"Loader not found: {args.loader}")
        sys.exit(1)
    if not Path(args.firmware_dir).exists():
        logger.error(f"Firmware dir not found: {args.firmware_dir}")
        sys.exit(1)

    run_unbrick(port=args.port, loader=args.loader, firmware_dir=args.firmware_dir)

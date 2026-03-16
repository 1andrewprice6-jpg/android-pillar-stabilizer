import os
import sys
import logging
from pathlib import Path

# config.py lives at workspace/ root, one level up from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
config.setup_env()

from edlclient.Library.Connection.seriallib import serial_class
from edlclient.Library.sahara import sahara
from edlclient.Library.firehose_client import firehose_client
from edlclient.Library.sahara_defs import sahara_mode_t, cmd_t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ULTIMATE_UNBRICK")

def run_unbrick():
    # Dynamic port scanning
    from edlclient.Library.Connection.seriallib import serial_class
    import serial.tools.list_ports

    target_port = None

    # 1. Try config port first
    print(f"Checking configured port {config.PORT}...")
    try:
        test = serial_class(portname=f"\\\\.\\{config.PORT}")
        if test.connect(portname=f"\\\\.\\{config.PORT}"):
            target_port = config.PORT
            print(f"Found device on {target_port}")
            test.close()
    except:
        pass

    # 2. If not found, scan all ports
    if not target_port:
        print("Scanning for Qualcomm QDLoader 9008...")
        ports = serial.tools.list_ports.comports()
        for p in ports:
            # Check for common VID:PID or Name
            if "9008" in p.description or (p.vid == 0x05C6 and p.pid == 0x9008):
                target_port = p.device
                print(f"Auto-detected device on {target_port} ({p.description})")
                break

    if not target_port:
        logger.error("Device NOT FOUND. Please connect device in EDL mode (Hold Vol+ & Vol- while plugging in).")
        # Optional: could loop here, but for now just exit to let the loop script handle it or user retry
        return

    port = target_port
    loader = str(config.LOADER_PATH)
    firmware_dir = str(config.FIRMWARE_ROOT)

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
    args = config.FIREHOSE_ARGS

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
    run_unbrick()

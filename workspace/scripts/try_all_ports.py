import logging
import sys
from pathlib import Path

# config.py lives at workspace/ root, one level up from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
config.setup_env()

from edlclient.Library.Connection.seriallib import serial_class
from edlclient.Library.sahara import sahara
from edlclient.Library.firehose_client import firehose_client
from edlclient.Library.sahara_defs import cmd_t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TRY_ALL_PORTS")

# Try COM3, COM4, COM7 (from Device Manager) plus COM5, COM6, COM8-COM20
PORTS_TO_TRY = ["COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "COM10",
                "COM11", "COM12", "COM13", "COM14", "COM15", "COM16", "COM17",
                "COM18", "COM19", "COM20"]

def try_port(port_name):
    """Try to connect and execute unbrick on a single port"""
    logger.info(f"\n{'='*60}")
    logger.info(f"TRYING PORT: {port_name}")
    logger.info(f"{'='*60}")

    try:
        # 1. Initialize Connection
        cdc = serial_class(loglevel=logging.WARNING)
        if not cdc.connect(portname=f"\\\\.\\{port_name}"):
            logger.warning(f"❌ Cannot connect to {port_name}")
            return False

        logger.info(f"✓ Connected to {port_name}")

        # 2. Sahara Handshake
        sahara_tool = sahara(cdc, loglevel=logging.INFO)
        sahara_tool.programmer = str(config.LOADER_PATH)

        logger.info("Attempting Sahara handshake...")
        res = sahara_tool.connect()
        logger.info(f"Sahara response: {res}")

        mode = "error"
        if "mode" in res:
            if res["mode"] == "sahara":
                if "cmd" in res and res["cmd"] == cmd_t.SAHARA_HELLO_REQ:
                    logger.info("🔄 Uploading loader...")
                    mode = sahara_tool.upload_loader(version=2)
                    logger.info(f"Loader upload result: {mode}")
                elif "cmd" in res and res["cmd"] == cmd_t.SAHARA_END_TRANSFER:
                    logger.info("Device already in firehose mode")
                    mode = "firehose"
            else:
                mode = res["mode"]

        if mode != "firehose":
            logger.error(f"❌ Failed to enter Firehose mode (current: {mode})")
            return False

        # 3. Firehose Connection
        logger.info("🔥 Entering Firehose...")
        args = config.FIREHOSE_ARGS

        fh = firehose_client(args, cdc, sahara_tool, logging.INFO, print)
        if fh.connect(sahara_tool):
            logger.info(f"\n{'='*60}")
            logger.info(f"✓✓✓ SUCCESS ON {port_name} ✓✓✓")
            logger.info(f"{'='*60}\n")

            # Read GPT
            logger.info("📋 Reading GPT...")
            fh.printgpt()

            # Ask before flashing
            logger.info("\n" + "="*60)
            logger.info("DEVICE READY - GPT READ SUCCESSFUL")
            logger.info("="*60)

            response = input("\nProceed with FULL FLASH? (yes/no): ").strip().lower()
            if response == "yes":
                logger.info("🚀 Starting full flash...")
                # Execute flash with rawprogram and patch
                if fh.cmd_program(config.FIREHOSE_ARGS["<rawprogram>"], config.FIREHOSE_ARGS["<patch>"]):
                    logger.info("\n✓✓✓ FLASH COMPLETED SUCCESSFULLY ✓✓✓")
                else:
                    logger.error("Flash failed")
            else:
                logger.info("Flash cancelled by user")

            return True
        else:
            logger.error(f"❌ Failed to connect to Firehose on {port_name}")
            return False

    except Exception as e:
        logger.error(f"❌ Error on {port_name}: {e}")
        return False

def main():
    logger.info(f"Loader path: {config.LOADER_PATH}")
    logger.info(f"Firmware dir: {config.FIRMWARE_ROOT}")
    logger.info(f"\nScanning {len(PORTS_TO_TRY)} COM ports...\n")

    for port in PORTS_TO_TRY:
        if try_port(port):
            logger.info(f"\n✓ Successfully connected via {port}")
            return

    logger.error("\n❌ No valid EDL connection found on any port")
    logger.info("\nTroubleshooting:")
    logger.info("1. Ensure device is in EDL mode (both volume buttons + USB)")
    logger.info("2. Check Device Manager for Qualcomm HS-USB QDLoader 9008")
    logger.info("3. Install/update Qualcomm USB drivers")
    logger.info("4. Try a different USB cable/port")

if __name__ == "__main__":
    main()

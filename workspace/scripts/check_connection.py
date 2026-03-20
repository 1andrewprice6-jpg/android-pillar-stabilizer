import sys
import logging
from pathlib import Path

# config.py lives at workspace/ root, one level up from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
config.setup_env()

from edlclient.Library.Connection.seriallib import serial_class
from edlclient.Library.sahara import sahara

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CHECK_CONN")

def check():
    port = config.PORT
    logger.info(f"Checking connection on {port}...")

    cdc = serial_class(loglevel=logging.INFO)
    if not cdc.connect(portname=f"\\\\.\\{port}"):
        logger.error(f"Device NOT FOUND on {port}. Ensure it's in EDL mode (9008).")
        return False

    logger.info("✓ Device detected!")

    sahara_tool = sahara(cdc, loglevel=logging.INFO)
    res = sahara_tool.connect()

    if res and "mode" in res:
        logger.info(f"✓ Sahara handshake successful! Mode: {res['mode']}")
        return True
    else:
        logger.error("Failed to perform Sahara handshake.")
        return False

if __name__ == "__main__":
    check()

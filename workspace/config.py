import os
from pathlib import Path

# Base project paths
WORKSPACE_DIR = Path(__file__).parent
PROJECT_ROOT = WORKSPACE_DIR.parent

# External paths (update these if the environment changes)
EDL_REPO_PATH = Path(r"C:\Users\Andrew Price\Lazarus_11\edl_repo")
FIRMWARE_ROOT = Path(r"C:\Users\Andrew Price\Desktop\CPH2451export_11_15.0.0.201EX01_2024120218280210_zip\CPH2451export_11_15.0.0.201EX01_2024120218280210_zip\op11\IMAGES")

# Device Configuration
PORT = "COM7"
LOADER_PATH = FIRMWARE_ROOT / "prog_firehose_ddr.elf"

# Firehose arguments
FIREHOSE_ARGS = {
    "--memory": "ufs",
    "--lun": None,
    "--skipstorageinit": True,
    "--debugmode": False,
    "--skipwrite": False,
    "--maxpayload": "0x100000",
    "--sectorsize": "4096",
    "--skipresponse": False,
    "--devicemodel": None,
    "--serial": None,
    "qfil": True,
    "<rawprogram>": "rawprogram0.xml",
    "<patch>": "patch0.xml",
    "<imagedir>": str(FIRMWARE_ROOT)
}

def setup_env():
    import sys
    if str(EDL_REPO_PATH) not in sys.path:
        sys.path.insert(0, str(EDL_REPO_PATH))
    return str(EDL_REPO_PATH)

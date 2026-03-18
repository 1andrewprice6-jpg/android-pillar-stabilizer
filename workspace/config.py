import os
from pathlib import Path

# Base project paths
WORKSPACE_DIR = Path(__file__).parent
PROJECT_ROOT = WORKSPACE_DIR.parent

# External paths (update these if the environment changes)
EDL_REPO_PATH = Path(r"C:\Users\Andrew Price\Desktop\edl-master\edl-master")

# bkerler edl repo on Desktop (has VIP-bypass loaders in Loaders/oppo/)
EDL_BKERLER_PATH = Path(r"C:\Users\Andrew Price\Desktop\edl-master\edl-master")

# bkerler/Loaders repo - device-specific Firehose loaders keyed by HWID+pkhash
# Clone with: workspace\scripts\setup_loaders.bat
# Repo: https://github.com/bkerler/Loaders.git
# loader_db.py auto-scans EDL_BKERLER_PATH/Loaders/ for the right SM8550 loader
LOADERS_DB_PATH = EDL_BKERLER_PATH / "Loaders" / "bkerler"

# Primary firmware source: OP11-AUTO-RECOVER flash_ready (complete, all 6 UFS LUNs)
FIRMWARE_ROOT = Path(r"C:\Users\Andrew Price\OP11-AUTO-RECOVER\flash_ready")

# Fallback firmware source (original export zip)
FIRMWARE_ROOT_ALT = Path(r"C:\Users\Andrew Price\Desktop\CPH2451export_11_15.0.0.201EX01_2024120218280210_zip\CPH2451export_11_15.0.0.201EX01_2024120218280210_zip\op11\IMAGES")

# Device Configuration
PORT = "COM5"

# Loader selection:
#   LOADER_PATH       - stock SM8550 loader from firmware package (1.6MB, Qualcomm-signed)
#   VIP_LOADER_PATH   - bkerler oppo VIP-bypass loader (948KB, bypasses Oppo auth check)
# SM8550 (Snapdragon 8 Gen 2) requires a valid signed loader; use stock unless it fails auth.
# If stock loader returns VIP/auth error, switch to VIP_LOADER_PATH.
LOADER_PATH = FIRMWARE_ROOT / "prog_firehose_ddr.elf"
VIP_LOADER_PATH = EDL_BKERLER_PATH / "Loaders" / "oppo" / "prog_firehose_ddr.elf"

# Set USE_VIP_LOADER = True to force the VIP-bypass loader (bkerler oppo)
USE_VIP_LOADER = False
ACTIVE_LOADER = VIP_LOADER_PATH if USE_VIP_LOADER else LOADER_PATH

# CPH2451 UFS LUN map (SM8550 / Snapdragon 8 Gen 2)
# LUN0: userdata, super, persist, GPT
# LUN1: xbl_a, xbl_config_a, apdp (Slot A bootloader)
# LUN2: xbl_b, xbl_config_b, apdpb (Slot B bootloader)
# LUN3: cdt, engineering_cdt, ddr (calibration/config)
# LUN4: main firmware - 84 partitions, A/B slots (modem, TZ, boot, DSP, etc.)
# LUN5: nvbk, modemst1/2, oplusreserve1-5 (modem calibration + reserves)
RAWPROGRAM_FILES = [f"rawprogram{i}.xml" for i in range(6)]
PATCH_FILES = [f"patch{i}.xml" for i in range(6)]

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

def get_active_loader():
    """Return the active loader path, preferring VIP loader if USE_VIP_LOADER is set."""
    loader = ACTIVE_LOADER
    if not loader.exists():
        # Fallback chain: VIP -> stock -> error
        if loader == VIP_LOADER_PATH and LOADER_PATH.exists():
            return LOADER_PATH
        raise FileNotFoundError(f"Loader not found: {loader}")
    return loader

EDL_PY = EDL_REPO_PATH / "edl.py"

def setup_env():
    import sys
    if str(EDL_REPO_PATH) not in sys.path:
        sys.path.insert(0, str(EDL_REPO_PATH))
    return str(EDL_REPO_PATH)

import sys
from pathlib import Path

# config.py lives at workspace/ root, one level up from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

fw_root = config.FIRMWARE_ROOT
rp_path = fw_root / "rawprogram0.xml"
patch_path = fw_root / "patch0.xml"

if rp_path.exists():
    print(f"✓ rawprogram0.xml found ({rp_path.stat().st_size} bytes)")
else:
    print("❌ rawprogram0.xml NOT FOUND")

if patch_path.exists():
    print(f"✓ patch0.xml found ({patch_path.stat().st_size} bytes)")
else:
    print("❌ patch0.xml NOT FOUND")

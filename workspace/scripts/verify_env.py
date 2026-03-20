import sys
from pathlib import Path

# Path to EDL repo
repo_path = Path(r"C:\Users\Andrew Price\Lazarus_11\edl_repo")
sys.path.insert(0, str(repo_path))

try:
    import edlclient
    print("✓ EDL Client library found and importable.")
    from edlclient.Library.Connection.seriallib import serial_class
    print("✓ Serial library importable.")
except ImportError as e:
    print(f"❌ Error importing EDL library: {e}")
    sys.exit(1)

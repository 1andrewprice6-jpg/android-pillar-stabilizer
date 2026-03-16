import time
import sys
import subprocess
import logging
from pathlib import Path

# config.py lives at workspace/ root, one level up from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

from edlclient.Library.Connection.seriallib import serial_class
import serial.tools.list_ports

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("MONITOR")

def scan_for_device():
    # Scan for Qualcomm 9008
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "9008" in p.description or (p.vid == 0x05C6 and p.pid == 0x9008):
            return p.device
    return None

def main():
    print("="*60)
    print("EDL MONITOR & AUTO-FLASH")
    print("="*60)
    print("Waiting for device... (Press Ctrl+C to stop)")
    print("Instructions: Power off -> Hold Vol+ & Vol- -> Plug USB")

    while True:
        port = scan_for_device()
        if port:
            print(f"\n[!] Device detected on {port}!")
            print("Starting Unbrick process...")

            # Run the unbrick script
            # We can import and run it directly or subprocess
            # Subprocess is safer to ensure clean state
            try:
                subprocess.run([sys.executable, "ULTIMATE_UNBRICK_REAL.py"], check=True)
                print("\n[+] Unbrick script finished successfully!")
                break
            except subprocess.CalledProcessError:
                print("\n[-] Unbrick script failed. Retrying scan in 5 seconds...")
                time.sleep(5)
        else:
            # Print a dot every second to show life
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(1)

if __name__ == "__main__":
    main()

import serial
import serial.tools.list_ports

def scan_all_com():
    print("Scanning COM ports for potential Qualcomm devices...")
    for i in range(256):
        port = f"COM{i}"
        try:
            s = serial.Serial(port)
            print(f"✓ Found ACTIVE port: {port}")
            s.close()
        except (serial.SerialException, FileNotFoundError):
            pass

if __name__ == "__main__":
    scan_all_com()

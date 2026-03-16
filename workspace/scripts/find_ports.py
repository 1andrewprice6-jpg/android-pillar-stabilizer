import serial.tools.list_ports
import serial

def find_ports():
    print("Listing all available serial ports:")
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        print(f"{port}: {desc} [{hwid}]")

if __name__ == "__main__":
    find_ports()

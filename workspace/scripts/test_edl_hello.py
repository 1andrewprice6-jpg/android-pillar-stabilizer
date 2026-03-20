import serial
import time
import binascii

def send_sahara_hello(port):
    try:
        print(f"Opening {port}...")
        ser = serial.Serial(port, 115200, timeout=1)

        # Sahara Hello Packet (Command 1, Length 48, Version 2, Swapped)
        # 01 00 00 00 30 00 00 00 02 00 00 00 ... (and so on)
        # Actually, let's just read first. If device is in Sahara, it might be sending HELLO.

        print("Reading initial bytes (if any)...")
        initial = ser.read(64)
        if initial:
            print(f"Received: {binascii.hexlify(initial)}")
        else:
            print("No initial data received. Sending probe...")
            # Try sending a simple 00 byte or a ping
            ser.write(b'\x00'*4)
            resp = ser.read(64)
            print(f"Response: {binascii.hexlify(resp)}")

        ser.close()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    send_sahara_hello("COM5")

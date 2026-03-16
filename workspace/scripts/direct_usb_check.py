import os
import sys
import time

# Set UTF-8 for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')

print("=" * 60)
print("DIRECT USB ACCESS - BYPASS WINDOWS SERIAL")
print("=" * 60)

try:
    import usb.core
    import usb.util

    # Qualcomm EDL mode: VID=05C6, PID=9008
    VID = 0x05C6
    PID = 0x9008

    print(f"\nSearching for Qualcomm EDL device (VID:{VID:04X} PID:{PID:04X})...")

    # Find all USB devices
    devices = usb.core.find(find_all=True)
    device_list = list(devices)

    print(f"\nFound {len(device_list)} total USB devices")

    # Look specifically for EDL device
    edl_device = usb.core.find(idVendor=VID, idProduct=PID)

    if edl_device is None:
        print("\n[X] EDL device NOT FOUND via USB")
        print("\nAll connected USB devices:")
        for dev in device_list:
            try:
                print(f"  - VID:{dev.idVendor:04X} PID:{dev.idProduct:04X}")
            except:
                pass

        print("\nTroubleshooting:")
        print("1. Disconnect phone completely")
        print("2. Hold Vol+ and Vol- together")
        print("3. While holding, plug in USB cable")
        print("4. Device should appear as Qualcomm HS-USB QDLoader 9008")

    else:
        print("\n[OK] EDL DEVICE FOUND!")
        print(f"  Bus: {edl_device.bus}")
        print(f"  Address: {edl_device.address}")
        print(f"  VID:PID = {edl_device.idVendor:04X}:{edl_device.idProduct:04X}")

        try:
            manufacturer = usb.util.get_string(edl_device, edl_device.iManufacturer)
            product = usb.util.get_string(edl_device, edl_device.iProduct)
            print(f"  Manufacturer: {manufacturer}")
            print(f"  Product: {product}")
        except:
            print("  (Unable to read device strings - may need admin rights)")

        # Try to detach kernel driver if active (Linux)
        if sys.platform != 'win32':
            try:
                if edl_device.is_kernel_driver_active(0):
                    edl_device.detach_kernel_driver(0)
                    print("  Detached kernel driver")
            except:
                pass

        # Try to set configuration
        try:
            edl_device.set_configuration()
            print("  [OK] Device configured successfully")

            # Get configuration
            cfg = edl_device.get_active_configuration()
            intf = cfg[(0,0)]

            # Find endpoints
            ep_out = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )

            ep_in = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )

            if ep_out and ep_in:
                print(f"  [OK] OUT endpoint: 0x{ep_out.bEndpointAddress:02X}")
                print(f"  [OK] IN endpoint: 0x{ep_in.bEndpointAddress:02X}")
                print("\n  >>> DEVICE IS READY FOR EDL COMMUNICATION <<<")
            else:
                print("  [!] Endpoints not found")

        except usb.core.USBError as e:
            print(f"  [!] USB Error: {e}")
            if "Access is denied" in str(e) or "Entity not found" in str(e):
                print("  [!] This may require:")
                print("      - Running as Administrator")
                print("      - Installing WinUSB/libusb driver with Zadig")
        except Exception as e:
            print(f"  [!] Error: {e}")

except ImportError:
    print("\n[!] PyUSB not installed")
    print("Run: pip install pyusb")
    sys.exit(1)

"""
Shared pytest configuration for the OnePlus 11 (CPH2451) recovery test suite.

Stubs out hardware-dependent packages (pyusb, pyserial) before any project
modules are imported, so tests run cleanly in CI without USB hardware.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path so test files can import project modules
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _stub_module(name):
    """Register a dummy module so imports don't fail in CI."""
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]


# ---- pyusb stubs (no USB hardware in CI) -------------------------------------
usb_mod = _stub_module("usb")
usb_core_mod = _stub_module("usb.core")
usb_util_mod = _stub_module("usb.util")
if not hasattr(usb_core_mod, "find"):
    usb_core_mod.find = lambda **kwargs: None  # No device found
if not hasattr(usb_core_mod, "USBError"):
    usb_core_mod.USBError = Exception
if not hasattr(usb_util_mod, "dispose_resources"):
    usb_util_mod.dispose_resources = lambda dev: None
# Wire submodules onto the usb stub so `import usb.core` finds them via attribute
usb_mod.core = usb_core_mod
usb_mod.util = usb_util_mod

# ---- pyserial stubs ----------------------------------------------------------
serial_mod = _stub_module("serial")
if not hasattr(serial_mod, "Serial"):
    serial_mod.Serial = MagicMock
if not hasattr(serial_mod, "SerialException"):
    serial_mod.SerialException = Exception
serial_tools = _stub_module("serial.tools")
serial_tools_lp = _stub_module("serial.tools.list_ports")
if not hasattr(serial_tools_lp, "comports"):
    serial_tools_lp.comports = lambda: []  # No ports in CI
serial_mod.tools = serial_tools
serial_tools.list_ports = serial_tools_lp

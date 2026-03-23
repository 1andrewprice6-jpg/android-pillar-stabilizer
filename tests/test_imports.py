"""
CI smoke tests for the OnePlus 11 (CPH2451) recovery tool.

These tests run without hardware and without the edl package installed.
They validate:
  - All Python modules are syntactically valid and importable (mocking USB deps)
  - Core utility functions (path finders, XML parsers, config loading) work correctly
  - ULTIMATE_UNBRICK_REAL helpers behave correctly on missing inputs
"""

import sys
import os
import json
import types
import importlib
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path so we can import project modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Helpers — stub out hardware-dependent packages before any imports
# ---------------------------------------------------------------------------

def _stub_module(name):
    """Register a dummy module so imports don't fail in CI."""
    if name not in sys.modules:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    return sys.modules[name]


# Stub pyusb (no USB hardware in CI)
usb_mod = _stub_module("usb")
usb_core_mod = _stub_module("usb.core")
usb_util_mod = _stub_module("usb.util")
usb_core_mod.find = lambda **kwargs: None  # No device found
usb_core_mod.USBError = Exception
usb_util_mod.dispose_resources = lambda dev: None

# Stub serial / pyserial
serial_mod = _stub_module("serial")
serial_mod.Serial = MagicMock
serial_mod.SerialException = Exception
serial_tools = _stub_module("serial.tools")
serial_tools_lp = _stub_module("serial.tools.list_ports")
serial_tools_lp.comports = lambda: []  # No ports in CI
# Wire serial.tools and serial.tools.list_ports onto the serial stub
serial_mod.tools = serial_tools
serial_tools.list_ports = serial_tools_lp


# ---------------------------------------------------------------------------
# Tests: module imports
# ---------------------------------------------------------------------------

class TestModuleImports:
    """All project modules should import cleanly in a no-hardware CI environment."""

    def test_import_edl_helper(self):
        import edl_helper  # noqa: F401
        assert hasattr(edl_helper, "EDLHelper")

    def test_import_edl_recovery(self):
        import EDLRecovery  # noqa: F401
        assert hasattr(EDLRecovery, "QualcommRecover")
        assert hasattr(EDLRecovery, "SaharaProtocol")
        assert hasattr(EDLRecovery, "FirehoseProtocol")

    def test_import_flash_device(self):
        import FlashDevice  # noqa: F401
        assert hasattr(FlashDevice, "EDLDevice")

    def test_import_recovery_orchestrator(self):
        import RecoveryOrchestrator  # noqa: F401
        assert hasattr(RecoveryOrchestrator, "RecoveryOrchestrator")
        assert hasattr(RecoveryOrchestrator, "RecoveryState")
        assert hasattr(RecoveryOrchestrator, "AssetValidator")

    def test_import_oneplus_cph2451(self):
        import OnePlusRevive_CPH2451  # noqa: F401
        assert hasattr(OnePlusRevive_CPH2451, "OnePlusReviveTool")

    def test_import_ultimate_unbrick(self):
        import ULTIMATE_UNBRICK_REAL as ub  # noqa: F401
        assert hasattr(ub, "run_unbrick")
        assert hasattr(ub, "find_edl_tool")
        assert hasattr(ub, "find_edl_port")
        assert hasattr(ub, "flash_lun")


# ---------------------------------------------------------------------------
# Tests: find_edl_port returns None when no device present
# ---------------------------------------------------------------------------

class TestFindEdlPort:
    def test_returns_none_when_no_device(self):
        from ULTIMATE_UNBRICK_REAL import find_edl_port
        # serial_tools_lp.comports returns [] (stubbed above)
        result = find_edl_port()
        assert result is None


# ---------------------------------------------------------------------------
# Tests: run_unbrick rejects bad inputs gracefully
# ---------------------------------------------------------------------------

class TestRunUnbrickValidation:
    def test_no_edl_tool_returns_false(self):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value=None):
            result = run_unbrick(loader="/nonexistent.elf", firmware_dir="/nonexistent")
        assert result is False

    def test_missing_loader_returns_false(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"):
            result = run_unbrick(
                loader=str(tmp_path / "missing.elf"),
                firmware_dir=str(tmp_path)
            )
        assert result is False

    def test_missing_firmware_dir_returns_false(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        # Create a dummy loader file
        loader = tmp_path / "prog_firehose_ddr.elf"
        loader.write_bytes(b"\x7fELF" + b"\x00" * 100)
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"):
            result = run_unbrick(
                loader=str(loader),
                firmware_dir=str(tmp_path / "nonexistent_fw")
            )
        assert result is False

    def test_no_rawprogram_xml_returns_false(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        loader = tmp_path / "prog_firehose_ddr.elf"
        loader.write_bytes(b"\x7fELF" + b"\x00" * 100)
        # No rawprogram0.xml in tmp_path
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"):
            with patch("ULTIMATE_UNBRICK_REAL.find_edl_port", return_value="COM5"):
                result = run_unbrick(
                    loader=str(loader),
                    firmware_dir=str(tmp_path)
                )
        assert result is False


# ---------------------------------------------------------------------------
# Tests: EDLHelper XML parsing
# ---------------------------------------------------------------------------

class TestEDLHelperParsing:
    def _make_rawprogram_xml(self, tmp_path):
        """Create a minimal rawprogram0.xml fixture."""
        xml_content = """<?xml version="1.0" ?>
<data>
  <program label="xbl_a"    filename="xbl.elf"    start_sector="256"  num_partition_sectors="512" />
  <program label="boot_a"   filename="boot.img"   start_sector="1024" num_partition_sectors="8192" />
  <program label="system_a" filename="system.img" start_sector="16384" num_partition_sectors="131072" />
</data>
"""
        xml_file = tmp_path / "rawprogram0.xml"
        xml_file.write_text(xml_content)
        return xml_file

    def test_list_partitions_returns_correct_count(self, tmp_path):
        from edl_helper import EDLHelper
        xml_file = self._make_rawprogram_xml(tmp_path)
        partitions = EDLHelper.list_partitions(str(xml_file))
        assert len(partitions) == 3

    def test_list_partitions_correct_labels(self, tmp_path):
        from edl_helper import EDLHelper
        xml_file = self._make_rawprogram_xml(tmp_path)
        partitions = EDLHelper.list_partitions(str(xml_file))
        labels = [p["label"] for p in partitions]
        assert "xbl_a" in labels
        assert "boot_a" in labels
        assert "system_a" in labels

    def test_list_partitions_missing_file(self):
        from edl_helper import EDLHelper
        result = EDLHelper.list_partitions("/nonexistent/path/rawprogram0.xml")
        assert result == []

    def test_validate_firmware_structure_fails_on_empty_dir(self, tmp_path):
        from edl_helper import EDLHelper
        assert EDLHelper.validate_firmware_structure(str(tmp_path)) is False

    def test_validate_firmware_structure_passes_with_required_files(self, tmp_path):
        from edl_helper import EDLHelper
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "prog_firehose_ddr.elf").write_bytes(b"\x7fELF" + b"\x00" * 100)
        assert EDLHelper.validate_firmware_structure(str(tmp_path)) is True


# ---------------------------------------------------------------------------
# Tests: RecoveryOrchestrator asset validation
# ---------------------------------------------------------------------------

class TestAssetValidator:
    def _make_firmware_dir(self, tmp_path):
        """Populate a minimal valid firmware directory."""
        loader = tmp_path / "prog_firehose_ddr.elf"
        loader.write_bytes(b"\x7fELF" + b"\x00" * 200_000)  # > 100 KB

        # AssetValidator requires min 1 KB for XML files — pad with comments
        padding = "<!-- " + "x" * 1100 + " -->"
        rawprogram = tmp_path / "rawprogram0.xml"
        rawprogram.write_text(
            f'<data>'
            f'<program label="xbl_a" filename="" start_sector="0" num_partition_sectors="0"/>'
            f'{padding}'
            f'</data>'
        )

        patch_xml = tmp_path / "patch0.xml"
        patch_xml.write_text(
            f'<data>'
            f'<patch label="xbl_a" filename="" start_sector="0" num_sectors="0"/>'
            f'{padding}'
            f'</data>'
        )
        return tmp_path

    def test_passes_with_all_required_files(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        self._make_firmware_dir(tmp_path)
        validator = AssetValidator(str(tmp_path))
        result = validator.validate_required_assets()
        assert result is True

    def test_fails_on_missing_loader(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        validator = AssetValidator(str(tmp_path))
        result = validator.validate_required_assets()
        assert result is False

    def test_fails_on_missing_rawprogram(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        loader = tmp_path / "prog_firehose_ddr.elf"
        loader.write_bytes(b"\x7fELF" + b"\x00" * 200_000)
        (tmp_path / "patch0.xml").write_text("<data/>")
        validator = AssetValidator(str(tmp_path))
        result = validator.validate_required_assets()
        assert result is False


# ---------------------------------------------------------------------------
# Tests: edl_config.json is valid JSON with required keys
# ---------------------------------------------------------------------------

class TestEdlConfig:
    def test_config_is_valid_json(self):
        config_path = PROJECT_ROOT / "edl_config.json"
        assert config_path.exists(), "edl_config.json must exist"
        with open(config_path) as f:
            config = json.load(f)
        assert isinstance(config, dict)

    def test_config_has_device_section(self):
        config_path = PROJECT_ROOT / "edl_config.json"
        with open(config_path) as f:
            config = json.load(f)
        assert "device" in config
        assert config["device"]["model"] == "CPH2451"

    def test_programmer_is_relative(self):
        config_path = PROJECT_ROOT / "edl_config.json"
        with open(config_path) as f:
            config = json.load(f)
        programmer = config.get("programmer", "")
        # Programmer should be a relative filename, not an absolute Windows path
        assert not programmer.startswith("C:\\"), (
            f"programmer should be relative, got: {programmer}"
        )


# ---------------------------------------------------------------------------
# Tests: OnePlusReviveTool device info
# ---------------------------------------------------------------------------

class TestOnePlusReviveTool:
    def test_device_info_model(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        info = tool.get_device_info()
        assert info["model"] == "CPH2451"
        assert info["chipset"] == "SM8550"

    def test_set_loader_path(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        tool.set_loader_path("/some/path")
        assert tool.loader_path == "/some/path"

    def test_validate_loaders_false_on_missing_dir(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        tool.set_loader_path("/nonexistent/directory")
        assert tool.validate_loaders() is False

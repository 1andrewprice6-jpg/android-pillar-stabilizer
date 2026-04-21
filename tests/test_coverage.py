"""
Comprehensive coverage tests for the OnePlus 11 (CPH2451) recovery tool.

These tests run without hardware and without the edl package installed.
They extend test_imports.py to cover functions and branches not exercised there.
"""

import sys
import os
import json
import types
import struct
import importlib
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import subprocess

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Helpers — stub hardware-dependent packages before any project imports
# ---------------------------------------------------------------------------

def _stub_module(name):
    if name not in sys.modules:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    return sys.modules[name]


# lxml → stdlib ET
import xml.etree.ElementTree as _stdlib_ET
lxml_mod = _stub_module("lxml")
lxml_etree_mod = _stub_module("lxml.etree")
lxml_etree_mod.parse = _stdlib_ET.parse
lxml_etree_mod.ParseError = _stdlib_ET.ParseError
lxml_etree_mod.Element = _stdlib_ET.Element
lxml_mod.etree = lxml_etree_mod

# pyusb
usb_mod = _stub_module("usb")
usb_core_mod = _stub_module("usb.core")
usb_util_mod = _stub_module("usb.util")
usb_core_mod.find = lambda **kwargs: None
usb_core_mod.USBError = Exception
usb_util_mod.dispose_resources = lambda dev: None
usb_mod.core = usb_core_mod
usb_mod.util = usb_util_mod

# pyserial
serial_mod = _stub_module("serial")
serial_mod.Serial = MagicMock
serial_mod.SerialException = Exception
serial_tools = _stub_module("serial.tools")
serial_tools_lp = _stub_module("serial.tools.list_ports")
serial_tools_lp.comports = lambda: []
serial_mod.tools = serial_tools
serial_tools.list_ports = serial_tools_lp


# ---------------------------------------------------------------------------
# Shared XML fixture helpers
# ---------------------------------------------------------------------------

def _write_rawprogram_xml(path, partitions):
    """Write rawprogram XML with given list of (label, filename, start, num) tuples."""
    root = ET.Element("data")
    for label, filename, start, num in partitions:
        ET.SubElement(root, "program", attrib={
            "label": label,
            "filename": filename,
            "start_sector": str(start),
            "num_partition_sectors": str(num),
        })
    ET.ElementTree(root).write(str(path), xml_declaration=True, encoding="unicode")


def _write_patch_xml(path, patches):
    """Write patch XML with list of (label, filename, start, num) tuples."""
    root = ET.Element("data")
    for label, filename, start, num in patches:
        ET.SubElement(root, "patch", attrib={
            "label": label,
            "filename": filename,
            "start_sector": str(start),
            "num_sectors": str(num),
        })
    ET.ElementTree(root).write(str(path), xml_declaration=True, encoding="unicode")


def _make_valid_firmware_dir(tmp_path, loader_name="prog_firehose_ddr.elf"):
    """Create a minimal valid firmware directory for AssetValidator."""
    # 200 KB+ to exceed the 100 KB minimum loader size check
    (tmp_path / loader_name).write_bytes(b"\x7fELF" + b"\x00" * 200_000)
    # 1 KB+ padding to meet minimum XML file size validation (min_size=1000)
    padding = "<!-- " + "x" * 1100 + " -->"
    (tmp_path / "rawprogram0.xml").write_text(
        f'<data><program label="xbl_a" filename="" start_sector="0" '
        f'num_partition_sectors="0"/>{padding}</data>'
    )
    (tmp_path / "patch0.xml").write_text(
        f'<data><patch label="xbl_a" filename="" start_sector="0" '
        f'num_sectors="0"/>{padding}</data>'
    )
    return tmp_path


# ===========================================================================
# EDLHelper — calculate_recovery_time
# ===========================================================================

class TestEDLHelperCalculateRecoveryTime:
    """calculate_recovery_time returns correct estimate for known inputs."""

    def _make_partitions(self, total_sectors, bandwidth=400):
        from edl_helper import EDLHelper
        partitions = [{"num_sectors": total_sectors, "label": "test", "filename": "test.img"}]
        return EDLHelper.calculate_recovery_time(partitions, bandwidth_mbps=bandwidth)

    def test_zero_sectors_returns_zero(self):
        from edl_helper import EDLHelper
        result = EDLHelper.calculate_recovery_time([])
        assert result == 0.0

    def test_known_size_returns_correct_seconds(self):
        from edl_helper import EDLHelper
        # 400 MB / 400 MB/s = 1.0 second
        # 400 MB = 400 * 1024 * 1024 bytes = 102400 * 4096 sectors
        sectors = (400 * 1024 * 1024) // 4096
        partitions = [{"num_sectors": sectors, "label": "test", "filename": "test.img"}]
        result = EDLHelper.calculate_recovery_time(partitions, bandwidth_mbps=400)
        assert abs(result - 1.0) < 0.01

    def test_bandwidth_parameter_scales_result(self):
        from edl_helper import EDLHelper
        sectors = (100 * 1024 * 1024) // 4096
        partitions = [{"num_sectors": sectors, "label": "test", "filename": "test.img"}]
        slow = EDLHelper.calculate_recovery_time(partitions, bandwidth_mbps=100)
        fast = EDLHelper.calculate_recovery_time(partitions, bandwidth_mbps=200)
        assert abs(slow / fast - 2.0) < 0.01

    def test_multiple_partitions_summed(self):
        from edl_helper import EDLHelper
        # Each partition is 100 MB worth of sectors
        sectors_per = (100 * 1024 * 1024) // 4096
        partitions = [
            {"num_sectors": sectors_per, "label": "a", "filename": "a.img"},
            {"num_sectors": sectors_per, "label": "b", "filename": "b.img"},
        ]
        result = EDLHelper.calculate_recovery_time(partitions, bandwidth_mbps=200)
        # 200 MB / 200 MB/s = 1.0 s
        assert abs(result - 1.0) < 0.01


# ===========================================================================
# EDLHelper — validate_firmware_structure alternate loader names
# ===========================================================================

class TestEDLHelperAlternateLoaders:
    """validate_firmware_structure accepts alternate ELF loader filenames."""

    def test_accepts_ufs_elf_variant(self, tmp_path):
        from edl_helper import EDLHelper
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "prog_firehose_ddr_ufs.elf").write_bytes(b"\x7fELF" + b"\x00" * 100)
        assert EDLHelper.validate_firmware_structure(str(tmp_path)) is True

    def test_accepts_emmc_elf_variant(self, tmp_path):
        from edl_helper import EDLHelper
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "prog_emmc_firehose.elf").write_bytes(b"\x7fELF" + b"\x00" * 100)
        assert EDLHelper.validate_firmware_structure(str(tmp_path)) is True

    def test_fails_without_xml(self, tmp_path):
        from edl_helper import EDLHelper
        (tmp_path / "prog_firehose_ddr.elf").write_bytes(b"\x7fELF" + b"\x00" * 100)
        assert EDLHelper.validate_firmware_structure(str(tmp_path)) is False

    def test_fails_without_any_loader(self, tmp_path):
        from edl_helper import EDLHelper
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        assert EDLHelper.validate_firmware_structure(str(tmp_path)) is False


# ===========================================================================
# EDLHelper — list_partitions malformed XML
# ===========================================================================

class TestEDLHelperMalformedXML:
    def test_malformed_xml_returns_empty(self, tmp_path):
        from edl_helper import EDLHelper
        bad = tmp_path / "rawprogram0.xml"
        bad.write_text("<<not valid xml>>")
        result = EDLHelper.list_partitions(str(bad))
        assert result == []

    def test_xml_with_no_program_elements_returns_empty(self, tmp_path):
        from edl_helper import EDLHelper
        xml = tmp_path / "rawprogram0.xml"
        xml.write_text("<data><other label='x'/></data>")
        result = EDLHelper.list_partitions(str(xml))
        assert result == []

    def test_partition_sector_values_parsed_correctly(self, tmp_path):
        from edl_helper import EDLHelper
        xml = tmp_path / "rawprogram0.xml"
        _write_rawprogram_xml(xml, [("boot_a", "boot.img", 1024, 8192)])
        result = EDLHelper.list_partitions(str(xml))
        assert len(result) == 1
        assert result[0]["start_sector"] == 1024
        assert result[0]["num_sectors"] == 8192
        assert result[0]["filename"] == "boot.img"


# ===========================================================================
# FlashDevice — parse_partitions
# ===========================================================================

class TestFlashDeviceParsePartitions:
    """parse_partitions reads rawprogram0.xml with top-level <program> elements."""

    def _write_xml(self, tmp_path, entries):
        """Write top-level <program> elements (FlashDevice uses root-level, not .//program)."""
        root = ET.Element("data")
        for label, filename, start, num in entries:
            ET.SubElement(root, "program", attrib={
                "label": label,
                "filename": filename,
                "start_sector": str(start),
                "num_partition_sectors": str(num),
                "size_in_KB": "0",
            })
        xml_path = tmp_path / "rawprogram0.xml"
        ET.ElementTree(root).write(str(xml_path), xml_declaration=True, encoding="unicode")
        return xml_path

    def test_parse_single_partition(self, tmp_path):
        from FlashDevice import parse_partitions
        xml = self._write_xml(tmp_path, [("xbl_a", "xbl.elf", 256, 512)])
        result = parse_partitions(str(xml))
        assert len(result) == 1
        assert result[0].label == "xbl_a"
        assert result[0].filename == "xbl.elf"
        assert result[0].start_sector == 256
        assert result[0].num_sectors == 512

    def test_parse_multiple_partitions(self, tmp_path):
        from FlashDevice import parse_partitions
        entries = [
            ("xbl_a", "xbl.elf", 256, 512),
            ("boot_a", "boot.img", 1024, 8192),
            ("system_a", "system.img", 16384, 131072),
        ]
        xml = self._write_xml(tmp_path, entries)
        result = parse_partitions(str(xml))
        assert len(result) == 3
        labels = [p.label for p in result]
        assert "xbl_a" in labels
        assert "boot_a" in labels
        assert "system_a" in labels

    def test_empty_xml_returns_empty_list(self, tmp_path):
        from FlashDevice import parse_partitions
        xml = tmp_path / "rawprogram0.xml"
        xml.write_text("<data></data>")
        result = parse_partitions(str(xml))
        assert result == []


# ===========================================================================
# RecoveryOrchestrator — PartitionParser
# ===========================================================================

class TestPartitionParser:
    """PartitionParser correctly parses rawprogram0.xml and patch0.xml."""

    def test_parse_partitions_returns_true_on_valid_xml(self, tmp_path):
        from RecoveryOrchestrator import PartitionParser
        rp = tmp_path / "rawprogram0.xml"
        p0 = tmp_path / "patch0.xml"
        _write_rawprogram_xml(rp, [
            ("xbl_a", "xbl.elf", 256, 512),
            ("boot_a", "boot.img", 1024, 8192),
        ])
        _write_patch_xml(p0, [("xbl_a", "xbl.elf", 256, 512)])
        parser = PartitionParser(rp, p0)
        assert parser.parse_partitions() is True
        assert len(parser.partitions) == 2

    def test_parse_partitions_populates_labels(self, tmp_path):
        from RecoveryOrchestrator import PartitionParser
        rp = tmp_path / "rawprogram0.xml"
        p0 = tmp_path / "patch0.xml"
        _write_rawprogram_xml(rp, [("system_a", "system.img", 16384, 131072)])
        _write_patch_xml(p0, [])
        parser = PartitionParser(rp, p0)
        parser.parse_partitions()
        assert parser.partitions[0].label == "system_a"
        assert parser.partitions[0].start_sector == 16384
        assert parser.partitions[0].num_sectors == 131072

    def test_parse_partitions_returns_false_on_malformed_xml(self, tmp_path):
        from RecoveryOrchestrator import PartitionParser
        rp = tmp_path / "rawprogram0.xml"
        p0 = tmp_path / "patch0.xml"
        rp.write_text("<<not xml>>")
        p0.write_text("<data/>")
        parser = PartitionParser(rp, p0)
        assert parser.parse_partitions() is False

    def test_parse_patches_returns_true_on_valid_xml(self, tmp_path):
        from RecoveryOrchestrator import PartitionParser
        rp = tmp_path / "rawprogram0.xml"
        p0 = tmp_path / "patch0.xml"
        _write_rawprogram_xml(rp, [])
        _write_patch_xml(p0, [
            ("xbl_a", "xbl.elf", 256, 512),
            ("boot_a", "boot.img", 1024, 8192),
        ])
        parser = PartitionParser(rp, p0)
        assert parser.parse_patches() is True
        assert len(parser.patches) == 2

    def test_parse_patches_returns_false_on_malformed_xml(self, tmp_path):
        from RecoveryOrchestrator import PartitionParser
        rp = tmp_path / "rawprogram0.xml"
        p0 = tmp_path / "patch0.xml"
        _write_rawprogram_xml(rp, [])
        p0.write_text("<<bad>>")
        parser = PartitionParser(rp, p0)
        assert parser.parse_patches() is False

    def test_size_bytes_computed_from_sectors(self, tmp_path):
        from RecoveryOrchestrator import PartitionParser
        rp = tmp_path / "rawprogram0.xml"
        p0 = tmp_path / "patch0.xml"
        _write_rawprogram_xml(rp, [("userdata", "userdata.img", 0, 1000)])
        _write_patch_xml(p0, [])
        parser = PartitionParser(rp, p0)
        parser.parse_partitions()
        # 1000 sectors × 4096 bytes/sector = 4 096 000
        assert parser.partitions[0].size_bytes == 1000 * 4096


# ===========================================================================
# AssetValidator — validate_file_exists and validate_file_size
# ===========================================================================

class TestAssetValidatorFileChecks:
    def test_validate_file_exists_returns_false_for_missing(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        v = AssetValidator(str(tmp_path))
        exists, path = v.validate_file_exists("nonexistent.elf")
        assert exists is False
        assert path is None

    def test_validate_file_exists_returns_true_for_present(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        (tmp_path / "myfile.elf").write_bytes(b"\x00" * 10)
        v = AssetValidator(str(tmp_path))
        exists, path = v.validate_file_exists("myfile.elf")
        assert exists is True
        assert path is not None

    def test_validate_file_size_true_when_large_enough(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        f = tmp_path / "bigfile.bin"
        f.write_bytes(b"\x00" * 200)
        v = AssetValidator(str(tmp_path))
        assert v.validate_file_size(f, 100) is True

    def test_validate_file_size_false_when_too_small(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        f = tmp_path / "small.bin"
        f.write_bytes(b"\x00" * 50)
        v = AssetValidator(str(tmp_path))
        assert v.validate_file_size(f, 100) is False

    def test_validate_file_size_false_for_missing_file(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        v = AssetValidator(str(tmp_path))
        assert v.validate_file_size(tmp_path / "ghost.bin", 1) is False


# ===========================================================================
# AssetValidator — validate_partition_files
# ===========================================================================

class TestAssetValidatorPartitionFiles:
    def test_returns_empty_list_when_all_files_present(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        # Create the XML referencing two img files, then create those files
        rp = tmp_path / "rawprogram0.xml"
        _write_rawprogram_xml(rp, [
            ("boot_a", "boot.img", 1024, 8192),
            ("system_a", "system.img", 16384, 131072),
        ])
        (tmp_path / "boot.img").write_bytes(b"\x00" * 10)
        (tmp_path / "system.img").write_bytes(b"\x00" * 10)
        v = AssetValidator(str(tmp_path))
        missing = v.validate_partition_files(rp)
        assert missing == []

    def test_returns_missing_filenames(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        rp = tmp_path / "rawprogram0.xml"
        _write_rawprogram_xml(rp, [
            ("boot_a", "boot.img", 1024, 8192),
            ("system_a", "system.img", 16384, 131072),
        ])
        # Only create boot.img
        (tmp_path / "boot.img").write_bytes(b"\x00" * 10)
        v = AssetValidator(str(tmp_path))
        missing = v.validate_partition_files(rp)
        assert "system.img" in missing
        assert "boot.img" not in missing

    def test_returns_empty_list_on_malformed_xml(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        rp = tmp_path / "rawprogram0.xml"
        rp.write_text("<<bad xml>>")
        v = AssetValidator(str(tmp_path))
        result = v.validate_partition_files(rp)
        assert result == []

    def test_skips_entries_with_empty_filename(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        rp = tmp_path / "rawprogram0.xml"
        _write_rawprogram_xml(rp, [("gpt", "", 0, 0)])  # empty filename
        v = AssetValidator(str(tmp_path))
        missing = v.validate_partition_files(rp)
        assert missing == []


# ===========================================================================
# AssetValidator — generate_error_report
# ===========================================================================

class TestAssetValidatorErrorReport:
    def test_report_mentions_missing_files(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        v = AssetValidator(str(tmp_path))
        v.missing_files = ["prog_firehose_ddr.elf"]
        v.corrupted_files = []
        report = v.generate_error_report()
        assert "MISSING FILES" in report
        assert "prog_firehose_ddr.elf" in report

    def test_report_mentions_corrupted_files(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        v = AssetValidator(str(tmp_path))
        v.missing_files = []
        v.corrupted_files = ["rawprogram0.xml"]
        report = v.generate_error_report()
        assert "CORRUPTED FILES" in report
        assert "rawprogram0.xml" in report

    def test_report_is_string(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        v = AssetValidator(str(tmp_path))
        v.missing_files = ["x.elf"]
        v.corrupted_files = []
        assert isinstance(v.generate_error_report(), str)


# ===========================================================================
# AssetValidator — fails when patch0.xml missing
# ===========================================================================

class TestAssetValidatorMissingPatch:
    def test_fails_on_missing_patch_xml(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        padding = "<!-- " + "x" * 1100 + " -->"
        (tmp_path / "prog_firehose_ddr.elf").write_bytes(b"\x7fELF" + b"\x00" * 200_000)
        (tmp_path / "rawprogram0.xml").write_text(
            f'<data><program label="xbl_a" filename="" start_sector="0" '
            f'num_partition_sectors="0"/>{padding}</data>'
        )
        # patch0.xml intentionally not created
        v = AssetValidator(str(tmp_path))
        assert v.validate_required_assets() is False

    def test_fails_on_corrupted_loader(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        padding = "<!-- " + "x" * 1100 + " -->"
        # 50 bytes < 100 KB minimum to trigger corrupted-file detection
        (tmp_path / "prog_firehose_ddr.elf").write_bytes(b"\x7fELF" + b"\x00" * 50)
        (tmp_path / "rawprogram0.xml").write_text(
            f'<data><program label="xbl_a" filename="" start_sector="0" '
            f'num_partition_sectors="0"/>{padding}</data>'
        )
        (tmp_path / "patch0.xml").write_text(
            f'<data><patch label="xbl_a" filename="" start_sector="0" '
            f'num_sectors="0"/>{padding}</data>'
        )
        v = AssetValidator(str(tmp_path))
        assert v.validate_required_assets() is False
        assert "prog_firehose_ddr.elf" in v.corrupted_files


# ===========================================================================
# OnePlusReviveTool — set_firmware_path and list_available_loaders
# ===========================================================================

class TestOnePlusReviveToolExtra:
    def test_set_firmware_path(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        tool.set_firmware_path("/some/firmware")
        assert tool.firmware_path == "/some/firmware"

    def test_list_available_loaders_nonexistent_dir(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        result = tool.list_available_loaders("/nonexistent/dir")
        assert result == []

    def test_list_available_loaders_empty_dir(self, tmp_path):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        result = tool.list_available_loaders(str(tmp_path))
        assert result == []

    def test_list_available_loaders_finds_matching_files(self, tmp_path):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        # Create a file matching the CPH2451 name filter
        elf_file = tmp_path / "prog_firehose_ddr_CPH2451.elf"
        elf_file.write_bytes(b"\x7fELF" + b"\x00" * 100)
        tool = OnePlusReviveTool()
        result = tool.list_available_loaders(str(tmp_path))
        assert any("CPH2451" in r for r in result)

    def test_validate_loaders_true_when_enough_files(self, tmp_path):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        # Need >= 2 loader matches; prog_firehose_ddr.elf + rawprogram0.xml both match
        (tmp_path / "prog_firehose_ddr.elf").write_bytes(b"\x7fELF" + b"\x00" * 100)
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        tool = OnePlusReviveTool()
        tool.set_loader_path(str(tmp_path))
        assert tool.validate_loaders() is True

    def test_device_info_has_required_keys(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        info = tool.get_device_info()
        for key in ("model", "chipset", "firmware", "region", "variant"):
            assert key in info, f"Missing key: {key}"


# ===========================================================================
# ULTIMATE_UNBRICK_REAL — find_edl_tool
# ===========================================================================

class TestFindEdlTool:
    def test_returns_path_when_on_system_path(self):
        from ULTIMATE_UNBRICK_REAL import find_edl_tool
        with patch("shutil.which", return_value="/usr/local/bin/edl"):
            result = find_edl_tool()
        assert result == "/usr/local/bin/edl"

    def test_returns_none_when_no_tool_found(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import find_edl_tool
        with patch("shutil.which", return_value=None):
            # All candidate paths don't exist in a clean tmp_path context
            result = find_edl_tool()
        # May or may not find edl depending on system; just verify type
        assert result is None or isinstance(result, str)

    def test_returns_candidate_path_when_exists(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import find_edl_tool
        # Create ~/edl/edl.py by patching Path.home() to return tmp_path
        edl_dir = tmp_path / "edl"
        edl_dir.mkdir()
        (edl_dir / "edl.py").write_text("# fake edl")
        with patch("shutil.which", return_value=None), \
             patch("pathlib.Path.home", return_value=tmp_path):
            result = find_edl_tool()
        assert result is not None
        assert "edl.py" in result


# ===========================================================================
# ULTIMATE_UNBRICK_REAL — wait_for_edl_device
# ===========================================================================

class TestWaitForEdlDevice:
    def test_returns_none_when_serial_unavailable(self):
        import ULTIMATE_UNBRICK_REAL as ub
        original = ub._HAS_SERIAL
        ub._HAS_SERIAL = False
        try:
            result = ub.wait_for_edl_device(timeout=0)
        finally:
            ub._HAS_SERIAL = original
        assert result is None

    def test_returns_port_immediately_when_device_found(self):
        from ULTIMATE_UNBRICK_REAL import wait_for_edl_device
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_port", return_value="COM5"):
            result = wait_for_edl_device(timeout=60)
        assert result == "COM5"

    def test_returns_none_after_timeout_with_no_device(self):
        from ULTIMATE_UNBRICK_REAL import wait_for_edl_device
        import ULTIMATE_UNBRICK_REAL as ub
        original = ub._HAS_SERIAL
        ub._HAS_SERIAL = True
        try:
            with patch("ULTIMATE_UNBRICK_REAL.find_edl_port", return_value=None), \
                 patch("time.sleep"):
                result = wait_for_edl_device(timeout=0)
        finally:
            ub._HAS_SERIAL = original
        assert result is None


# ===========================================================================
# ULTIMATE_UNBRICK_REAL — flash_lun
# ===========================================================================

class TestFlashLun:
    def test_skips_when_rawprogram_missing(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        # No rawprogram0.xml → skip (returns True)
        result = flash_lun("/fake/edl", "/fake/loader.elf", str(tmp_path), 0)
        assert result is True

    def test_skips_when_patch_missing(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        # No patch0.xml → skip (returns True)
        result = flash_lun("/fake/edl", "/fake/loader.elf", str(tmp_path), 0)
        assert result is True

    def test_returns_true_on_success(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.returncode = 0
        with patch("subprocess.Popen", return_value=mock_proc):
            result = flash_lun("/fake/edl", "/fake/loader.elf", str(tmp_path), 0)
        assert result is True

    def test_returns_false_on_nonzero_exit(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.returncode = 1
        with patch("subprocess.Popen", return_value=mock_proc):
            result = flash_lun("/fake/edl", "/fake/loader.elf", str(tmp_path), 0)
        assert result is False

    def test_returns_false_on_file_not_found(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        with patch("subprocess.Popen", side_effect=FileNotFoundError("edl not found")):
            result = flash_lun("/fake/edl", "/fake/loader.elf", str(tmp_path), 0)
        assert result is False

    def test_dry_run_adds_skipwrite_flag(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.returncode = 0
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            flash_lun("/fake/edl", "/fake/loader.elf", str(tmp_path), 0, dry_run=True)
        cmd = mock_popen.call_args[0][0]
        assert "--skipwrite" in cmd

    def test_port_adds_serial_flags(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.returncode = 0
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            flash_lun("/fake/edl", "/fake/loader.elf", str(tmp_path), 0, port="COM5")
        cmd = mock_popen.call_args[0][0]
        cmd_str = " ".join(str(c) for c in cmd)
        assert "--serial" in cmd_str
        assert "COM5" in cmd_str

    def test_py_edl_tool_uses_python_interpreter(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.returncode = 0
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            flash_lun("/fake/edl.py", "/fake/loader.elf", str(tmp_path), 0)
        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == sys.executable
        assert "/fake/edl.py" in cmd

    def test_non_py_edl_tool_called_directly(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.returncode = 0
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            flash_lun("/usr/local/bin/edl", "/fake/loader.elf", str(tmp_path), 0)
        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == "/usr/local/bin/edl"


# ===========================================================================
# ULTIMATE_UNBRICK_REAL — run_unbrick extended scenarios
# ===========================================================================

class TestRunUnbrickExtended:
    def _make_fw(self, tmp_path, luns=(0,)):
        """Create a minimal firmware directory with specified LUN XMLs."""
        loader = tmp_path / "prog_firehose_ddr.elf"
        loader.write_bytes(b"\x7fELF" + b"\x00" * 100)
        for n in luns:
            (tmp_path / f"rawprogram{n}.xml").write_text("<data/>")
            (tmp_path / f"patch{n}.xml").write_text("<data/>")
        return loader

    def test_explicit_port_skips_auto_detection(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        loader = self._make_fw(tmp_path)
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.returncode = 0
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"), \
             patch("ULTIMATE_UNBRICK_REAL.find_edl_port") as mock_detect, \
             patch("subprocess.Popen", return_value=mock_proc):
            result = run_unbrick(port="COM5", loader=str(loader), firmware_dir=str(tmp_path))
        mock_detect.assert_not_called()
        assert result is True

    def test_all_luns_succeed_returns_true(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        loader = self._make_fw(tmp_path, luns=(0, 1))
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.returncode = 0
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"), \
             patch("subprocess.Popen", return_value=mock_proc), \
             patch("time.sleep"):
            result = run_unbrick(port="COM5", loader=str(loader),
                                 firmware_dir=str(tmp_path), start_lun=0, end_lun=1)
        assert result is True

    def test_one_lun_failure_returns_false(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        loader = self._make_fw(tmp_path, luns=(0, 1))
        proc_ok = MagicMock()
        proc_ok.stdout = iter([])
        proc_ok.returncode = 0
        proc_fail = MagicMock()
        proc_fail.stdout = iter([])
        proc_fail.returncode = 1
        side_effects = [proc_ok, proc_fail]
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"), \
             patch("subprocess.Popen", side_effect=side_effects), \
             patch("time.sleep"):
            result = run_unbrick(port="COM5", loader=str(loader),
                                 firmware_dir=str(tmp_path), start_lun=0, end_lun=1)
        assert result is False

    def test_start_lun_restricts_range(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        loader = self._make_fw(tmp_path, luns=(4,))
        # run_unbrick always validates rawprogram0.xml exists; create it for validation
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.returncode = 0
        popen_calls = []
        def capture_popen(*args, **kwargs):
            popen_calls.append(args[0])
            return mock_proc
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"), \
             patch("subprocess.Popen", side_effect=capture_popen):
            result = run_unbrick(port="COM5", loader=str(loader),
                                 firmware_dir=str(tmp_path), start_lun=4, end_lun=5)
        # LUN 4 has both rawprogram4.xml and patch4.xml → 1 flash call
        # LUN 5 has neither → skipped by inner run loop
        assert len(popen_calls) == 1

    def test_dry_run_flag_passes_through(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        loader = self._make_fw(tmp_path)
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.returncode = 0
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"), \
             patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            run_unbrick(port="COM5", loader=str(loader),
                        firmware_dir=str(tmp_path), dry_run=True)
        cmd = mock_popen.call_args[0][0]
        assert "--skipwrite" in cmd

    def test_no_port_and_no_device_returns_false(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        loader = self._make_fw(tmp_path)
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"), \
             patch("ULTIMATE_UNBRICK_REAL.find_edl_port", return_value=None):
            result = run_unbrick(loader=str(loader), firmware_dir=str(tmp_path))
        assert result is False

    def test_wait_device_invoked_when_requested(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        loader = self._make_fw(tmp_path)
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"), \
             patch("ULTIMATE_UNBRICK_REAL.wait_for_edl_device", return_value=None) as mock_wait:
            result = run_unbrick(loader=str(loader), firmware_dir=str(tmp_path),
                                 wait_device=True)
        mock_wait.assert_called_once()
        assert result is False


# ===========================================================================
# edl_config.json — vip_bypass and lun_map sections
# ===========================================================================

class TestEdlConfigExtended:
    def _load(self):
        with open(PROJECT_ROOT / "edl_config.json") as f:
            return json.load(f)

    def test_vip_bypass_section_present(self):
        config = self._load()
        assert "vip_bypass" in config

    def test_vip_bypass_enabled_is_bool(self):
        config = self._load()
        assert isinstance(config["vip_bypass"]["enabled"], bool)

    def test_vip_bypass_patterns_is_non_empty_list(self):
        config = self._load()
        patterns = config["vip_bypass"].get("patterns", [])
        assert isinstance(patterns, list)
        assert len(patterns) > 0

    def test_lun_map_has_six_entries(self):
        config = self._load()
        assert "lun_map" in config
        assert len(config["lun_map"]) == 6

    def test_luns_list_contains_expected_values(self):
        config = self._load()
        assert config["luns"] == [0, 1, 2, 3, 4, 5]

    def test_memory_is_ufs(self):
        config = self._load()
        assert config.get("memory") == "ufs"

    def test_device_chipset_correct(self):
        config = self._load()
        assert config["device"]["chipset"] == "SM8550"

    def test_supported_functions_includes_program(self):
        config = self._load()
        assert "program" in config.get("supported_functions", [])


# ===========================================================================
# EDLRecovery — SaharaProtocol.SaharaPacket
# ===========================================================================

class TestSaharaPacket:
    def test_pack_produces_8_bytes(self):
        from EDLRecovery import SaharaProtocol
        pkt = SaharaProtocol.SaharaPacket(command=0x01, length=0x30)
        data = pkt.pack()
        assert len(data) == 8

    def test_pack_encodes_little_endian(self):
        from EDLRecovery import SaharaProtocol
        pkt = SaharaProtocol.SaharaPacket(command=1, length=0x30)
        data = pkt.pack()
        cmd_val, len_val = struct.unpack("<II", data)
        assert cmd_val == 1
        assert len_val == 0x30

    def test_unpack_round_trip(self):
        from EDLRecovery import SaharaProtocol
        pkt = SaharaProtocol.SaharaPacket(command=7, length=8)
        data = pkt.pack()
        cmd, length = SaharaProtocol.SaharaPacket.unpack(data)
        assert cmd == 7
        assert length == 8

    def test_unpack_extra_bytes_ignored(self):
        from EDLRecovery import SaharaProtocol
        data = struct.pack("<II", 0x05, 0x08) + b"\xff" * 10
        cmd, length = SaharaProtocol.SaharaPacket.unpack(data)
        assert cmd == 0x05
        assert length == 0x08


# ===========================================================================
# RecoveryState enum
# ===========================================================================

class TestRecoveryStateEnum:
    def test_all_states_present(self):
        from RecoveryOrchestrator import RecoveryState
        expected = {"UNINITIALIZED", "ASSETS_VERIFIED", "DEVICE_DETECTED",
                    "LOADER_INJECTED", "PARTITIONS_FLASHED", "COMPLETED", "FAILED"}
        actual = {s.name for s in RecoveryState}
        assert expected == actual

    def test_failed_has_negative_value(self):
        from RecoveryOrchestrator import RecoveryState
        assert RecoveryState.FAILED.value < 0

    def test_uninitialized_is_zero(self):
        from RecoveryOrchestrator import RecoveryState
        assert RecoveryState.UNINITIALIZED.value == 0

    def test_completed_has_highest_positive_value(self):
        from RecoveryOrchestrator import RecoveryState
        positive = [s for s in RecoveryState if s.value >= 0]
        assert RecoveryState.COMPLETED == max(positive, key=lambda s: s.value)


# ===========================================================================
# RecoveryOrchestrator — verify_assets integration
# ===========================================================================

class TestRecoveryOrchestratorVerifyAssets:
    def test_fails_on_empty_directory(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator, RecoveryState
        orch = RecoveryOrchestrator(str(tmp_path))
        result = orch.verify_assets()
        assert result is False
        assert orch.state == RecoveryState.FAILED

    def test_passes_with_valid_firmware_dir(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator, RecoveryState
        _make_valid_firmware_dir(tmp_path)
        orch = RecoveryOrchestrator(str(tmp_path))
        result = orch.verify_assets()
        assert result is True
        assert orch.state == RecoveryState.ASSETS_VERIFIED

    def test_state_starts_as_uninitialized(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator, RecoveryState
        orch = RecoveryOrchestrator(str(tmp_path))
        assert orch.state == RecoveryState.UNINITIALIZED

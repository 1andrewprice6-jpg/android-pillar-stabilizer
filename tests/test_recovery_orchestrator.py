"""
Tests for RecoveryOrchestrator.py — asset validation, partition parser, orchestrator flow.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Padding so XML files exceed AssetValidator's 1 KB minimum
_XML_PAD = "<!-- " + "x" * 1100 + " -->"


def _make_valid_firmware(tmp_path):
    """Create a minimal valid firmware directory satisfying AssetValidator."""
    loader = tmp_path / "prog_firehose_ddr.elf"
    loader.write_bytes(b"\x7fELF" + b"\x00" * 200_000)  # > 100 KB

    rawprogram = tmp_path / "rawprogram0.xml"
    rawprogram.write_text(
        '<data>'
        '<program label="boot_a" filename="boot.img" '
        'start_sector="1024" num_partition_sectors="8192"/>'
        '<program label="system_a" filename="system.img" '
        'start_sector="9216" num_partition_sectors="131072"/>'
        f'{_XML_PAD}'
        '</data>'
    )

    patch_xml = tmp_path / "patch0.xml"
    patch_xml.write_text(
        '<data>'
        '<patch label="boot_a" filename="DISK" '
        'start_sector="1024" num_sectors="8192"/>'
        f'{_XML_PAD}'
        '</data>'
    )
    return tmp_path


# -----------------------------------------------------------------------------
# RecoveryState enum
# -----------------------------------------------------------------------------

class TestRecoveryState:
    def test_enum_values_are_distinct(self):
        from RecoveryOrchestrator import RecoveryState
        names = {s.name for s in RecoveryState}
        assert {"UNINITIALIZED", "ASSETS_VERIFIED", "DEVICE_DETECTED",
                "LOADER_INJECTED", "PARTITIONS_FLASHED", "COMPLETED",
                "FAILED"}.issubset(names)
        assert RecoveryState.FAILED.value == -1
        assert RecoveryState.UNINITIALIZED.value == 0


# -----------------------------------------------------------------------------
# _find_edl_tool helper
# -----------------------------------------------------------------------------

class TestFindEdlToolHelper:
    def test_returns_pip_command_when_available(self):
        from RecoveryOrchestrator import _find_edl_tool
        with patch("RecoveryOrchestrator.shutil.which", return_value="/usr/bin/edl"):
            assert _find_edl_tool() == "/usr/bin/edl"

    def test_returns_none_when_nothing_present(self):
        from RecoveryOrchestrator import _find_edl_tool
        with patch("RecoveryOrchestrator.shutil.which", return_value=None):
            with patch.object(Path, "exists", return_value=False):
                assert _find_edl_tool() is None


# -----------------------------------------------------------------------------
# AssetValidator
# -----------------------------------------------------------------------------

class TestAssetValidator:
    def test_validate_file_exists_returns_false_for_directory(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        v = AssetValidator(str(tmp_path))
        # Pass a directory name, not a file — should return False
        (tmp_path / "subdir").mkdir()
        exists, _ = v.validate_file_exists("subdir")
        assert exists is False

    def test_validate_file_exists_returns_false_for_missing(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        v = AssetValidator(str(tmp_path))
        exists, path = v.validate_file_exists("nonexistent.bin")
        assert exists is False and path is None

    def test_validate_file_size_too_small(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        v = AssetValidator(str(tmp_path))
        f = tmp_path / "tiny.bin"
        f.write_bytes(b"x")
        assert v.validate_file_size(f, min_size=1000) is False

    def test_validate_file_size_meets_minimum(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        v = AssetValidator(str(tmp_path))
        f = tmp_path / "big.bin"
        f.write_bytes(b"x" * 2000)
        assert v.validate_file_size(f, min_size=1000) is True

    def test_validate_file_size_oserror_returns_false(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        v = AssetValidator(str(tmp_path))
        bogus = tmp_path / "missing.bin"
        assert v.validate_file_size(bogus, min_size=1) is False

    def test_corrupted_loader_too_small(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        # Loader that exists but is below min_size threshold
        (tmp_path / "prog_firehose_ddr.elf").write_bytes(b"\x7fELF" + b"\x00" * 100)  # < 100 KB
        (tmp_path / "rawprogram0.xml").write_text("<data/>" + _XML_PAD)
        (tmp_path / "patch0.xml").write_text("<data/>" + _XML_PAD)
        v = AssetValidator(str(tmp_path))
        assert v.validate_required_assets() is False
        assert "prog_firehose_ddr.elf" in v.corrupted_files

    def test_validate_partition_files_reports_missing(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        xml = tmp_path / "rawprogram0.xml"
        xml.write_text(
            '<data>'
            '<program label="boot_a" filename="boot.img" start_sector="0" num_partition_sectors="1"/>'
            '<program label="system_a" filename="system.img" start_sector="0" num_partition_sectors="1"/>'
            '</data>'
        )
        # Create only one of the referenced .img files
        (tmp_path / "boot.img").write_bytes(b"\x00" * 100)
        v = AssetValidator(str(tmp_path))
        missing = v.validate_partition_files(xml)
        assert "system.img" in missing
        assert "boot.img" not in missing

    def test_validate_partition_files_handles_malformed_xml(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        bad = tmp_path / "rawprogram0.xml"
        bad.write_text("<not-valid")
        v = AssetValidator(str(tmp_path))
        assert v.validate_partition_files(bad) == []

    def test_generate_error_report_includes_missing_files(self, tmp_path):
        from RecoveryOrchestrator import AssetValidator
        v = AssetValidator(str(tmp_path))
        v.missing_files = ["foo.elf"]
        v.corrupted_files = ["bar.xml"]
        report = v.generate_error_report()
        assert "PRE-FLIGHT CHECK FAILED" in report
        assert "foo.elf" in report
        assert "bar.xml" in report


# -----------------------------------------------------------------------------
# PartitionParser
# -----------------------------------------------------------------------------

class TestPartitionParser:
    def test_parse_partitions_extracts_metadata(self, tmp_path):
        from RecoveryOrchestrator import PartitionParser
        rp = tmp_path / "rawprogram0.xml"
        rp.write_text(
            '<data>'
            '<program label="boot_a" filename="boot.img" '
            'start_sector="1024" num_partition_sectors="2048"/>'
            '<program label="system_a" filename="system.img" '
            'start_sector="3072" num_partition_sectors="65536"/>'
            '</data>'
        )
        pat = tmp_path / "patch0.xml"
        pat.write_text("<data/>")
        parser = PartitionParser(rp, pat)
        assert parser.parse_partitions() is True
        assert len(parser.partitions) == 2
        boot = parser.partitions[0]
        assert boot.label == "boot_a"
        assert boot.filename == "boot.img"
        assert boot.start_sector == 1024
        assert boot.num_sectors == 2048
        assert boot.size_bytes == 2048 * 4096

    def test_parse_partitions_handles_malformed_xml(self, tmp_path):
        from RecoveryOrchestrator import PartitionParser
        rp = tmp_path / "rawprogram0.xml"
        rp.write_text("<broken")
        pat = tmp_path / "patch0.xml"
        pat.write_text("<data/>")
        assert PartitionParser(rp, pat).parse_partitions() is False

    def test_parse_partitions_handles_missing_file(self, tmp_path):
        from RecoveryOrchestrator import PartitionParser
        parser = PartitionParser(tmp_path / "missing.xml", tmp_path / "missing2.xml")
        # parse_partitions should catch the OSError as "Unexpected error" and return False
        assert parser.parse_partitions() is False

    def test_parse_patches_extracts_metadata(self, tmp_path):
        from RecoveryOrchestrator import PartitionParser
        rp = tmp_path / "rawprogram0.xml"
        rp.write_text("<data/>")
        pat = tmp_path / "patch0.xml"
        pat.write_text(
            '<data>'
            '<patch label="xbl_a" filename="DISK" '
            'start_sector="0" num_sectors="64"/>'
            '</data>'
        )
        parser = PartitionParser(rp, pat)
        assert parser.parse_patches() is True
        assert len(parser.patches) == 1
        assert parser.patches[0].label == "xbl_a"
        assert parser.patches[0].num_sectors == 64

    def test_parse_patches_handles_malformed(self, tmp_path):
        from RecoveryOrchestrator import PartitionParser
        rp = tmp_path / "rawprogram0.xml"
        rp.write_text("<data/>")
        pat = tmp_path / "patch0.xml"
        pat.write_text("<broken")
        parser = PartitionParser(rp, pat)
        assert parser.parse_patches() is False


# -----------------------------------------------------------------------------
# RecoveryOrchestrator high-level flow (simulation mode)
# -----------------------------------------------------------------------------

class TestRecoveryOrchestrator:
    def test_initial_state_is_uninitialized(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator, RecoveryState
        orch = RecoveryOrchestrator(str(tmp_path))
        assert orch.state == RecoveryState.UNINITIALIZED
        assert orch.get_status() == "UNINITIALIZED"

    def test_verify_assets_fails_when_missing(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator, RecoveryState
        orch = RecoveryOrchestrator(str(tmp_path))
        assert orch.verify_assets() is False
        assert orch.state == RecoveryState.FAILED

    def test_verify_assets_succeeds_with_valid_firmware(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator, RecoveryState
        _make_valid_firmware(tmp_path)
        orch = RecoveryOrchestrator(str(tmp_path))
        assert orch.verify_assets() is True
        assert orch.state == RecoveryState.ASSETS_VERIFIED
        assert len(orch.parser.partitions) == 2
        assert len(orch.parser.patches) == 1

    def test_initialize_edl_simulation_when_no_tool(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator
        _make_valid_firmware(tmp_path)
        orch = RecoveryOrchestrator(str(tmp_path))
        orch.verify_assets()
        with patch("RecoveryOrchestrator._find_edl_tool", return_value=None):
            # Force EDLRecovery import to also fail by removing module from cache
            saved = sys.modules.pop("EDLRecovery", None)
            try:
                with patch.dict(sys.modules, {"EDLRecovery": None}):
                    result = orch.initialize_edl()
            finally:
                if saved is not None:
                    sys.modules["EDLRecovery"] = saved
        assert result is True  # simulation mode returns True
        assert orch.use_real_edl is False

    def test_inject_loader_simulation(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator, RecoveryState
        _make_valid_firmware(tmp_path)
        orch = RecoveryOrchestrator(str(tmp_path))
        orch.verify_assets()
        with patch("RecoveryOrchestrator.time.sleep"):
            assert orch.inject_loader() is True
        assert orch.state == RecoveryState.LOADER_INJECTED

    def test_flash_partitions_simulation(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator, RecoveryState
        _make_valid_firmware(tmp_path)
        orch = RecoveryOrchestrator(str(tmp_path))
        orch.verify_assets()
        # No edl_engine, no real edl tool => simulation path
        assert orch.flash_partitions() is True
        assert orch.state == RecoveryState.PARTITIONS_FLASHED

    def test_flash_partitions_without_parser_returns_false(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator
        orch = RecoveryOrchestrator(str(tmp_path))
        # parser is None until verify_assets() succeeds
        assert orch.flash_partitions() is False

    def test_apply_patches_with_no_parser(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator
        orch = RecoveryOrchestrator(str(tmp_path))
        assert orch.apply_patches() is False

    def test_apply_patches_succeeds(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator
        _make_valid_firmware(tmp_path)
        orch = RecoveryOrchestrator(str(tmp_path))
        orch.verify_assets()
        assert orch.apply_patches() is True

    def test_run_recovery_full_simulation_flow(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator, RecoveryState
        _make_valid_firmware(tmp_path)
        orch = RecoveryOrchestrator(str(tmp_path))
        with patch("RecoveryOrchestrator._find_edl_tool", return_value=None):
            with patch.dict(sys.modules, {"EDLRecovery": None}):
                with patch("RecoveryOrchestrator.time.sleep"):
                    result = orch.run_recovery()
        assert result is True
        assert orch.state == RecoveryState.COMPLETED

    def test_run_recovery_fails_on_invalid_assets(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator, RecoveryState
        orch = RecoveryOrchestrator(str(tmp_path))
        assert orch.run_recovery() is False
        assert orch.state == RecoveryState.FAILED

    def test_flash_partitions_real_edl_subprocess_path(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator, RecoveryState
        _make_valid_firmware(tmp_path)
        orch = RecoveryOrchestrator(str(tmp_path))
        orch.verify_assets()
        orch.use_real_edl = True
        orch.edl_tool_path = "/fake/edl.py"
        fake_proc = MagicMock()
        fake_proc.stdout = iter(["[edl] line1\n", "[edl] line2\n"])
        fake_proc.returncode = 0
        fake_proc.wait.return_value = 0
        with patch("RecoveryOrchestrator.subprocess.Popen", return_value=fake_proc):
            assert orch.flash_partitions() is True
        assert orch.state == RecoveryState.PARTITIONS_FLASHED

    def test_flash_partitions_real_edl_returns_false_on_nonzero_exit(self, tmp_path):
        from RecoveryOrchestrator import RecoveryOrchestrator
        _make_valid_firmware(tmp_path)
        orch = RecoveryOrchestrator(str(tmp_path))
        orch.verify_assets()
        orch.use_real_edl = True
        orch.edl_tool_path = "/fake/edl.py"
        fake_proc = MagicMock()
        fake_proc.stdout = iter(["error\n"])
        fake_proc.returncode = 1
        fake_proc.wait.return_value = 1
        with patch("RecoveryOrchestrator.subprocess.Popen", return_value=fake_proc):
            assert orch.flash_partitions() is False

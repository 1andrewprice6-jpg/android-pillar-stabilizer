"""
Tests for OnePlusRevive_CPH2451.py — recovery tool helpers and CLI.
"""

import io
import sys
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch, MagicMock


# -----------------------------------------------------------------------------
# OnePlusReviveTool — instance helpers
# -----------------------------------------------------------------------------

class TestOnePlusReviveToolHelpers:
    def test_set_firmware_path(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        tool.set_firmware_path("/some/firmware")
        assert tool.firmware_path == "/some/firmware"

    def test_validate_loaders_no_path(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        # loader_path defaults to None
        assert tool.validate_loaders() is False

    def test_validate_loaders_succeeds_with_required_files(self, tmp_path):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        # Need at least 2 matched patterns. Provide ELF + rawprogram XML.
        (tmp_path / "prog_firehose_ddr.elf").write_bytes(b"\x7fELF" + b"\x00" * 100)
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        tool = OnePlusReviveTool()
        tool.set_loader_path(str(tmp_path))
        assert tool.validate_loaders() is True

    def test_validate_loaders_fails_with_only_one_pattern(self, tmp_path):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        # Just an ELF — only one pattern matches; need >= 2
        (tmp_path / "loader.elf").write_bytes(b"\x7fELF")
        tool = OnePlusReviveTool()
        tool.set_loader_path(str(tmp_path))
        # Match prog_firehose_ddr (no), *.elf (yes) -> only 1 group, but actual code
        # extends loaders_found list and checks total length >= 2.
        # The single ".elf" file matches exactly one pattern => 1 file => False.
        assert tool.validate_loaders() is False


# -----------------------------------------------------------------------------
# check_edl_mode — no device path
# -----------------------------------------------------------------------------

class TestCheckEdlMode:
    def test_returns_false_when_no_device_present(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        with patch("serial.tools.list_ports.comports", return_value=[]):
            with patch("usb.core.find", return_value=None):
                assert tool.check_edl_mode() is False
        assert tool.device_connected is False

    def test_returns_true_when_serial_finds_device(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        port = MagicMock(); port.vid = 0x05C6; port.pid = 0x9008; port.device = "COM5"
        with patch("serial.tools.list_ports.comports", return_value=[port]):
            assert tool.check_edl_mode() is True
        assert tool.device_connected is True

    def test_returns_true_when_usb_finds_device(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        with patch("serial.tools.list_ports.comports", return_value=[]):
            with patch("usb.core.find", return_value=MagicMock()):
                assert tool.check_edl_mode() is True


# -----------------------------------------------------------------------------
# list_available_loaders
# -----------------------------------------------------------------------------

class TestListAvailableLoaders:
    def test_missing_directory_returns_empty(self, tmp_path):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        result = tool.list_available_loaders(str(tmp_path / "missing"))
        assert result == []

    def test_finds_matching_files(self, tmp_path):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        # Files containing "8550" or "CPH2451" in their path are matched
        (tmp_path / "prog_8550.elf").write_bytes(b"\x7fELF")
        (tmp_path / "loader_CPH2451.bin").write_bytes(b"x")
        (tmp_path / "unrelated.elf").write_bytes(b"x")  # should be filtered out
        tool = OnePlusReviveTool()
        result = tool.list_available_loaders(str(tmp_path))
        assert any("8550" in p for p in result)
        assert any("CPH2451" in p for p in result)
        assert not any("unrelated.elf" in p for p in result)

    def test_empty_directory_returns_empty(self, tmp_path):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        assert tool.list_available_loaders(str(tmp_path)) == []


# -----------------------------------------------------------------------------
# recovery_mode — early-exit guards
# -----------------------------------------------------------------------------

class TestRecoveryModeGuards:
    def test_aborts_when_no_device(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        with patch.object(tool, "check_edl_mode", return_value=False):
            assert tool.recovery_mode() is False

    def test_aborts_when_paths_missing(self):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        tool.device_connected = True
        # loader_path / firmware_path both None
        assert tool.recovery_mode() is False

    def test_aborts_when_loader_validation_fails(self, tmp_path):
        from OnePlusRevive_CPH2451 import OnePlusReviveTool
        tool = OnePlusReviveTool()
        tool.device_connected = True
        tool.set_loader_path(str(tmp_path))      # empty dir
        tool.set_firmware_path(str(tmp_path))
        assert tool.recovery_mode() is False


# -----------------------------------------------------------------------------
# CLI dispatch
# -----------------------------------------------------------------------------

class TestCli:
    def _run_main(self, argv):
        import OnePlusRevive_CPH2451 as mod
        with patch.object(sys, "argv", ["OnePlusRevive_CPH2451.py"] + argv):
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(io.StringIO()):
                try:
                    mod.main()
                    return 0, buf.getvalue()
                except SystemExit as exc:
                    return int(exc.code or 0), buf.getvalue()

    def test_no_args_prints_usage(self):
        rc, out = self._run_main([])
        assert rc == 0
        assert "Usage" in out

    def test_info_command(self):
        rc, _ = self._run_main(["info"])
        assert rc == 0

    def test_unknown_command_prints_usage(self):
        rc, out = self._run_main(["zzznotacommand"])
        assert rc == 0
        assert "Usage" in out

    def test_detect_command_runs(self):
        with patch("OnePlusRevive_CPH2451.OnePlusReviveTool.check_edl_mode",
                   return_value=False):
            rc, _ = self._run_main(["detect"])
        assert rc == 0

    def test_list_command_missing_arg_exits_one(self):
        rc, _ = self._run_main(["list"])
        assert rc == 1

    def test_recovery_command_missing_args_exits_one(self):
        rc, _ = self._run_main(["recovery"])
        assert rc == 1

    def test_list_command_with_dir(self, tmp_path):
        rc, _ = self._run_main(["list", str(tmp_path)])
        assert rc == 0

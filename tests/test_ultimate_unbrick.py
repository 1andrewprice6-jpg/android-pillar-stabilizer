"""
Tests for ULTIMATE_UNBRICK_REAL.py — EDL tool discovery, port wait, flash_lun.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock


# -----------------------------------------------------------------------------
# find_edl_tool
# -----------------------------------------------------------------------------

class TestFindEdlTool:
    def test_uses_pip_installed_command_first(self):
        from ULTIMATE_UNBRICK_REAL import find_edl_tool
        with patch("ULTIMATE_UNBRICK_REAL.shutil.which", return_value="/usr/local/bin/edl"):
            assert find_edl_tool() == "/usr/local/bin/edl"

    def test_falls_back_to_local_edl_py(self, tmp_path, monkeypatch):
        """When no installed `edl` command, fall back to a local edl.py next to candidates."""
        import ULTIMATE_UNBRICK_REAL as mod
        # Place a fake edl.py at one of the candidate locations under HOME
        fake_home = tmp_path / "home"
        (fake_home / "edl").mkdir(parents=True)
        fake_edl = fake_home / "edl" / "edl.py"
        fake_edl.write_text("# fake")
        monkeypatch.setenv("HOME", str(fake_home))
        with patch.object(mod.shutil, "which", return_value=None):
            # Path.home() reads $HOME at call time
            with patch.object(mod, "Path", Path):
                result = mod.find_edl_tool()
        # Either the fake_edl or another existing candidate may match — at minimum
        # the function must return a string ending in edl.py (not None / not raise).
        assert result is not None
        assert str(result).endswith("edl.py")

    def test_returns_none_when_nothing_found(self):
        from ULTIMATE_UNBRICK_REAL import find_edl_tool
        with patch("ULTIMATE_UNBRICK_REAL.shutil.which", return_value=None):
            with patch.object(Path, "exists", return_value=False):
                # Also force edlclient import to fail
                saved = sys.modules.pop("edlclient", None)
                sys.modules["edlclient"] = None  # force ImportError on next import
                try:
                    # Patch the import machinery to raise ImportError for edlclient
                    with patch.dict(sys.modules, {"edlclient": None}):
                        result = find_edl_tool()
                finally:
                    if saved is not None:
                        sys.modules["edlclient"] = saved
                    else:
                        sys.modules.pop("edlclient", None)
                assert result is None


# -----------------------------------------------------------------------------
# wait_for_edl_device
# -----------------------------------------------------------------------------

class TestWaitForEdlDevice:
    def test_returns_port_when_found_immediately(self):
        from ULTIMATE_UNBRICK_REAL import wait_for_edl_device
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_port", return_value="COM5"):
            assert wait_for_edl_device(timeout=1) == "COM5"

    def test_returns_none_after_timeout(self):
        from ULTIMATE_UNBRICK_REAL import wait_for_edl_device
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_port", return_value=None):
            with patch("ULTIMATE_UNBRICK_REAL.time.sleep"):
                # timeout=0 means deadline already passed; loop exits without a port
                result = wait_for_edl_device(timeout=0)
        assert result is None

    def test_no_serial_returns_none(self):
        import ULTIMATE_UNBRICK_REAL as mod
        with patch.object(mod, "_HAS_SERIAL", False):
            assert mod.wait_for_edl_device(timeout=5) is None


# -----------------------------------------------------------------------------
# find_edl_port (additional cases beyond the existing one)
# -----------------------------------------------------------------------------

class TestFindEdlPortExtra:
    def test_no_serial_module_returns_none(self):
        import ULTIMATE_UNBRICK_REAL as mod
        with patch.object(mod, "_HAS_SERIAL", False):
            assert mod.find_edl_port() is None

    def test_finds_qualcomm_device(self):
        from ULTIMATE_UNBRICK_REAL import find_edl_port
        port = MagicMock(); port.vid = 0x05C6; port.pid = 0x9008; port.device = "/dev/ttyUSB0"
        with patch("serial.tools.list_ports.comports", return_value=[port]):
            assert find_edl_port() == "/dev/ttyUSB0"

    def test_skips_non_qualcomm_devices(self):
        from ULTIMATE_UNBRICK_REAL import find_edl_port
        other = MagicMock(); other.vid = 0x1234; other.pid = 0x5678; other.device = "/dev/x"
        with patch("serial.tools.list_ports.comports", return_value=[other]):
            assert find_edl_port() is None


# -----------------------------------------------------------------------------
# flash_lun
# -----------------------------------------------------------------------------

class TestFlashLun:
    def test_skips_when_rawprogram_missing(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        # No rawprogram3.xml exists in tmp_path -> non-fatal skip, returns True
        result = flash_lun("/fake/edl", "/fake/loader.elf", str(tmp_path), 3)
        assert result is True

    def test_skips_when_patch_missing(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        # rawprogram exists but no patch -> skip
        (tmp_path / "rawprogram2.xml").write_text("<data/>")
        result = flash_lun("/fake/edl", "/fake/loader.elf", str(tmp_path), 2)
        assert result is True

    def test_returns_true_on_subprocess_success(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        fake_proc = MagicMock()
        fake_proc.stdout = iter(["doing work\n", "done\n"])
        fake_proc.returncode = 0
        fake_proc.wait.return_value = 0
        with patch("ULTIMATE_UNBRICK_REAL.subprocess.Popen", return_value=fake_proc):
            assert flash_lun("/fake/edl", "/fake/loader.elf",
                             str(tmp_path), 0, dry_run=True) is True

    def test_returns_false_on_subprocess_failure(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        fake_proc = MagicMock()
        fake_proc.stdout = iter(["error: bad firehose\n"])
        fake_proc.returncode = 1
        fake_proc.wait.return_value = 1
        with patch("ULTIMATE_UNBRICK_REAL.subprocess.Popen", return_value=fake_proc):
            assert flash_lun("/fake/edl", "/fake/loader.elf",
                             str(tmp_path), 0) is False

    def test_returns_false_on_filenotfound(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        with patch("ULTIMATE_UNBRICK_REAL.subprocess.Popen",
                   side_effect=FileNotFoundError):
            assert flash_lun("/missing/edl", "/fake/loader.elf",
                             str(tmp_path), 0) is False

    def test_returns_false_on_unexpected_exception(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        with patch("ULTIMATE_UNBRICK_REAL.subprocess.Popen",
                   side_effect=RuntimeError("boom")):
            assert flash_lun("/fake/edl", "/fake/loader.elf",
                             str(tmp_path), 0) is False

    def test_command_includes_dry_run_skipwrite_flag(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            p = MagicMock(); p.stdout = iter([]); p.returncode = 0; p.wait.return_value = 0
            return p

        with patch("ULTIMATE_UNBRICK_REAL.subprocess.Popen", side_effect=fake_popen):
            flash_lun("/fake/edl.py", "/fake/loader.elf", str(tmp_path), 0, dry_run=True)

        assert "--skipwrite" in captured["cmd"]
        # When tool ends in .py it should be invoked through Python interpreter
        assert captured["cmd"][0] == sys.executable
        assert "--memory=ufs" in captured["cmd"]

    def test_command_uses_direct_invocation_for_installed_tool(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import flash_lun
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            p = MagicMock(); p.stdout = iter([]); p.returncode = 0; p.wait.return_value = 0
            return p

        with patch("ULTIMATE_UNBRICK_REAL.subprocess.Popen", side_effect=fake_popen):
            flash_lun("/usr/local/bin/edl", "/fake/loader.elf", str(tmp_path), 0)

        assert captured["cmd"][0] == "/usr/local/bin/edl"
        assert "--skipwrite" not in captured["cmd"]


# -----------------------------------------------------------------------------
# run_unbrick — additional flow paths
# -----------------------------------------------------------------------------

class TestRunUnbrickFlow:
    def _make_min_firmware(self, tmp_path):
        (tmp_path / "prog_firehose_ddr.elf").write_bytes(b"\x7fELF" + b"\x00" * 100)
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "patch0.xml").write_text("<data/>")

    def test_no_loader_argument_returns_false(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"):
            result = run_unbrick(loader=None, firmware_dir=str(tmp_path))
        assert result is False

    def test_no_firmware_dir_argument_returns_false(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        loader = tmp_path / "loader.elf"
        loader.write_bytes(b"\x7fELF" + b"\x00" * 50)
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"):
            result = run_unbrick(loader=str(loader), firmware_dir=None)
        assert result is False

    def test_no_port_detected_returns_false(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        self._make_min_firmware(tmp_path)
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"):
            with patch("ULTIMATE_UNBRICK_REAL.find_edl_port", return_value=None):
                result = run_unbrick(
                    loader=str(tmp_path / "prog_firehose_ddr.elf"),
                    firmware_dir=str(tmp_path),
                )
        assert result is False

    def test_full_dry_run_succeeds(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        self._make_min_firmware(tmp_path)
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"):
            with patch("ULTIMATE_UNBRICK_REAL.find_edl_port", return_value="COM5"):
                with patch("ULTIMATE_UNBRICK_REAL.flash_lun", return_value=True):
                    with patch("ULTIMATE_UNBRICK_REAL.time.sleep"):
                        result = run_unbrick(
                            loader=str(tmp_path / "prog_firehose_ddr.elf"),
                            firmware_dir=str(tmp_path),
                            dry_run=True,
                            start_lun=0, end_lun=0,
                        )
        assert result is True

    def test_failed_lun_propagates_failure(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        self._make_min_firmware(tmp_path)
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"):
            with patch("ULTIMATE_UNBRICK_REAL.find_edl_port", return_value="COM5"):
                with patch("ULTIMATE_UNBRICK_REAL.flash_lun", return_value=False):
                    with patch("ULTIMATE_UNBRICK_REAL.time.sleep"):
                        result = run_unbrick(
                            loader=str(tmp_path / "prog_firehose_ddr.elf"),
                            firmware_dir=str(tmp_path),
                            start_lun=0, end_lun=0,
                        )
        assert result is False

    def test_wait_device_path_invoked(self, tmp_path):
        from ULTIMATE_UNBRICK_REAL import run_unbrick
        self._make_min_firmware(tmp_path)
        with patch("ULTIMATE_UNBRICK_REAL.find_edl_tool", return_value="/fake/edl"):
            with patch("ULTIMATE_UNBRICK_REAL.wait_for_edl_device", return_value="COM5") as wfe:
                with patch("ULTIMATE_UNBRICK_REAL.flash_lun", return_value=True):
                    with patch("ULTIMATE_UNBRICK_REAL.time.sleep"):
                        run_unbrick(
                            loader=str(tmp_path / "prog_firehose_ddr.elf"),
                            firmware_dir=str(tmp_path),
                            wait_device=True,
                            start_lun=0, end_lun=0,
                        )
        wfe.assert_called_once()

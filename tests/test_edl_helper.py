"""
Tests for edl_helper.py — EDL utility helpers and CLI.
"""

import io
import sys
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch, MagicMock


# -----------------------------------------------------------------------------
# EDLHelper.calculate_recovery_time
# -----------------------------------------------------------------------------

class TestCalculateRecoveryTime:
    def test_zero_partitions_returns_zero(self):
        from edl_helper import EDLHelper
        result = EDLHelper.calculate_recovery_time([])
        assert result == 0

    def test_single_partition_estimate(self):
        from edl_helper import EDLHelper
        # 256 sectors * 4096 = 1 MB exactly
        partitions = [{"label": "x", "filename": "x.img",
                       "start_sector": 0, "num_sectors": 256}]
        # 1 MB at 400 MB/s => 0.0025 seconds
        result = EDLHelper.calculate_recovery_time(partitions, bandwidth_mbps=400)
        assert abs(result - (1.0 / 400)) < 1e-6

    def test_custom_bandwidth(self):
        from edl_helper import EDLHelper
        partitions = [{"label": "x", "filename": "x.img",
                       "start_sector": 0, "num_sectors": 25600}]  # 100 MB
        result = EDLHelper.calculate_recovery_time(partitions, bandwidth_mbps=100)
        assert abs(result - 1.0) < 1e-6

    def test_multiple_partitions_sum(self):
        from edl_helper import EDLHelper
        partitions = [
            {"label": "a", "filename": "", "start_sector": 0, "num_sectors": 256},
            {"label": "b", "filename": "", "start_sector": 0, "num_sectors": 768},
        ]
        # 1 MB + 3 MB = 4 MB at 400 MB/s = 0.01 s
        result = EDLHelper.calculate_recovery_time(partitions, bandwidth_mbps=400)
        assert abs(result - 0.01) < 1e-6


# -----------------------------------------------------------------------------
# EDLHelper.detect_edl_device
# -----------------------------------------------------------------------------

class TestDetectEdlDevice:
    def test_no_device_returns_false(self):
        from edl_helper import EDLHelper
        # Default conftest stubs return [] from comports() and None from usb.core.find.
        # The EDLRecovery fallback constructs a QualcommRecover whose find_device()
        # also returns False without USB hardware.
        result = EDLHelper.detect_edl_device()
        assert result is False

    def test_serial_finds_device(self):
        from edl_helper import EDLHelper
        fake_port = MagicMock()
        fake_port.vid = 0x05C6
        fake_port.pid = 0x9008
        fake_port.device = "COM5"
        with patch("serial.tools.list_ports.comports", return_value=[fake_port]):
            assert EDLHelper.detect_edl_device() is True

    def test_serial_ignores_other_devices(self):
        from edl_helper import EDLHelper
        other = MagicMock(); other.vid = 0x1234; other.pid = 0x5678
        with patch("serial.tools.list_ports.comports", return_value=[other]):
            with patch("usb.core.find", return_value=None):
                # Falls through both detection paths; should return False without raising
                assert EDLHelper.detect_edl_device() is False

    def test_usb_finds_device_when_serial_empty(self):
        from edl_helper import EDLHelper
        with patch("serial.tools.list_ports.comports", return_value=[]):
            with patch("usb.core.find", return_value=MagicMock()):
                assert EDLHelper.detect_edl_device() is True


# -----------------------------------------------------------------------------
# EDLHelper.list_partitions: malformed XML handling
# -----------------------------------------------------------------------------

class TestListPartitionsMalformed:
    def test_invalid_xml_returns_empty_list(self, tmp_path):
        from edl_helper import EDLHelper
        bad = tmp_path / "broken.xml"
        bad.write_text("<not-valid xml")
        assert EDLHelper.list_partitions(str(bad)) == []

    def test_xml_with_no_program_entries(self, tmp_path):
        from edl_helper import EDLHelper
        empty = tmp_path / "empty.xml"
        empty.write_text("<data></data>")
        assert EDLHelper.list_partitions(str(empty)) == []

    def test_partition_uses_default_when_attrs_missing(self, tmp_path):
        from edl_helper import EDLHelper
        xml = tmp_path / "rawprogram0.xml"
        xml.write_text('<data><program/></data>')
        partitions = EDLHelper.list_partitions(str(xml))
        assert len(partitions) == 1
        assert partitions[0]["label"] == "unknown"
        assert partitions[0]["filename"] == ""
        assert partitions[0]["start_sector"] == 0


# -----------------------------------------------------------------------------
# CLI entry point: edl_helper.main
# -----------------------------------------------------------------------------

class TestEdlHelperCli:
    def _run_cli(self, argv):
        import edl_helper
        with patch.object(sys, "argv", ["edl_helper.py"] + argv):
            buf_out, buf_err = io.StringIO(), io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                rc = edl_helper.main()
        return rc

    def test_no_args_returns_zero(self):
        assert self._run_cli([]) == 0

    def test_detect_no_device_returns_one(self):
        with patch("edl_helper.EDLHelper.detect_edl_device", return_value=False):
            assert self._run_cli(["detect"]) == 1

    def test_detect_with_device_returns_zero(self):
        with patch("edl_helper.EDLHelper.detect_edl_device", return_value=True):
            assert self._run_cli(["detect"]) == 0

    def test_validate_missing_dir_returns_one(self, tmp_path):
        missing = tmp_path / "no_such_dir"
        assert self._run_cli(["validate", str(missing)]) == 1

    def test_validate_valid_dir_returns_zero(self, tmp_path):
        (tmp_path / "rawprogram0.xml").write_text("<data/>")
        (tmp_path / "prog_firehose_ddr.elf").write_bytes(b"\x7fELF" + b"\x00" * 100)
        assert self._run_cli(["validate", str(tmp_path)]) == 0

    def test_list_returns_zero(self, tmp_path):
        xml = tmp_path / "rawprogram0.xml"
        xml.write_text('<data><program label="boot_a" filename="boot.img" '
                       'start_sector="0" num_partition_sectors="1024"/></data>')
        assert self._run_cli(["list", str(xml)]) == 0

    def test_time_returns_zero(self, tmp_path):
        xml = tmp_path / "rawprogram0.xml"
        xml.write_text('<data><program label="boot_a" filename="boot.img" '
                       'start_sector="0" num_partition_sectors="1024"/></data>')
        assert self._run_cli(["time", str(xml), "--bandwidth", "200"]) == 0

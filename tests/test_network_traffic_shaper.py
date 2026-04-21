"""
Tests for network_traffic_shaper.py — placeholder transmission helpers.
"""

from unittest.mock import patch


class TestCustomEncode:
    def test_returns_list_with_input(self):
        from network_traffic_shaper import custom_encode
        result = custom_encode("hello")
        assert result == ["hello"]

    def test_handles_bytes(self):
        from network_traffic_shaper import custom_encode
        result = custom_encode(b"raw")
        assert result == [b"raw"]


class TestSendPacket:
    def test_send_packet_prints(self, capsys):
        from network_traffic_shaper import send_packet
        send_packet("payload")
        out = capsys.readouterr().out
        assert "payload" in out


class TestSendDummyTraffic:
    def test_invokes_sleep_with_duration(self):
        import network_traffic_shaper as mod
        with patch.object(mod.time, "sleep") as sleep_mock:
            mod.send_dummy_traffic(2)
        sleep_mock.assert_called_once_with(2)


class TestShapedTransmit:
    def test_shaped_transmit_invokes_pipeline(self, capsys):
        import network_traffic_shaper as mod
        with patch.object(mod.time, "sleep"):
            with patch.object(mod.random, "uniform", return_value=0.01):
                with patch.object(mod.random, "randint", return_value=1):
                    mod.shaped_transmit("DATA")
        out = capsys.readouterr().out
        # Should print a "Sending packet" line for the encoded payload
        assert "DATA" in out

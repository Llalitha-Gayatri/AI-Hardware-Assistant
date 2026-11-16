"""Unit tests for RAM inspection tool."""
from unittest.mock import patch
from app.tools.ram import inspect_ram, _parse_free_bytes, _parse_meminfo, format_bytes
from tests.conftest import MOCK_FREE_B, MOCK_PROC_MEMINFO


def test_format_bytes():
    assert "16.00 GB" in format_bytes(16 * 1024**3)
    assert "512.00 MB" in format_bytes(512 * 1024**2)
    assert "100 B" in format_bytes(100)


def test_parse_free_bytes():
    ram = _parse_free_bytes(MOCK_FREE_B)
    assert ram is not None
    assert ram.total_bytes == 16568852480
    assert ram.used_bytes == 6488248320
    assert ram.available_bytes == 9552429056
    assert ram.usage_percentage == 39.2
    assert "GB" in ram.total_human


def test_parse_meminfo():
    ram = _parse_meminfo(MOCK_PROC_MEMINFO)
    assert ram.total_bytes == 16180520 * 1024
    assert ram.available_bytes == 9328544 * 1024
    assert ram.usage_percentage is not None
    assert ram.error is None


@patch("app.tools.ram.execute_command")
def test_inspect_ram_fallback_to_meminfo(mock_exec):
    # Free command fails
    mock_exec.return_value = (127, "", "free not found")
    with patch("app.tools.ram.read_sysfs_or_proc_file", return_value=(MOCK_PROC_MEMINFO, None)):
        ram = inspect_ram()
        assert ram.total_bytes is not None
        assert ram.raw_source == "/proc/meminfo"
        assert ram.error is None

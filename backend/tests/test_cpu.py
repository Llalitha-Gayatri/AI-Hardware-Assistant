"""Unit tests for CPU inspection tool."""
import pytest
from unittest.mock import patch
from app.tools.cpu import inspect_cpu, _parse_lscpu_json, _parse_lscpu_text, _parse_proc_cpuinfo
from tests.conftest import MOCK_LSCPU_JSON, MOCK_LSCPU_TEXT, MOCK_PROC_CPUINFO
import json


def test_parse_lscpu_json():
    data = json.loads(MOCK_LSCPU_JSON)
    cpu = _parse_lscpu_json(data)

    assert "AMD Ryzen 7 5800H" in cpu.model
    assert cpu.architecture == "x86_64"
    assert cpu.cores == 8
    assert cpu.threads == 16
    assert cpu.max_frequency_mhz == 4462.5
    assert cpu.virtualization == "AMD-V"
    assert cpu.error is None


def test_parse_lscpu_text():
    cpu = _parse_lscpu_text(MOCK_LSCPU_TEXT)

    assert "i7-12700H" in cpu.model
    assert cpu.architecture == "x86_64"
    assert cpu.cores == 14
    assert cpu.threads == 20
    assert cpu.max_frequency_mhz == 4700.0
    assert cpu.virtualization == "VT-x"


def test_parse_proc_cpuinfo():
    cpu = _parse_proc_cpuinfo(MOCK_PROC_CPUINFO)

    assert "i7-12700H" in cpu.model
    assert cpu.architecture == "x86_64"
    assert cpu.cores == 14
    assert cpu.threads == 2
    assert cpu.virtualization == "VT-x (Intel)"


@patch("app.tools.cpu.execute_command")
def test_inspect_cpu_missing_utility(mock_exec):
    mock_exec.return_value = (127, "", "lscpu not found")
    with patch("app.tools.cpu.read_sysfs_or_proc_file", return_value=(None, "File not found")):
        cpu = inspect_cpu()
        assert cpu.model == "Unknown"
        assert cpu.error is not None
        assert "not available" in cpu.error or "not found" in cpu.error

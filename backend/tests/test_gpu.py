"""Unit tests for GPU inspection tool."""
from unittest.mock import patch
from app.tools.gpu import inspect_gpu, _parse_lspci_text
from tests.conftest import MOCK_LSPCI_DUAL_GPU, MOCK_LSPCI_AMD


def test_parse_lspci_dual_gpu():
    devices = _parse_lspci_text(MOCK_LSPCI_DUAL_GPU)
    assert len(devices) == 2

    intel = next((d for d in devices if "Intel" in d.vendor), None)
    assert intel is not None
    assert "Alder Lake" in intel.model
    assert intel.pci_id == "00:02.0"

    nvidia = next((d for d in devices if "NVIDIA" in d.vendor), None)
    assert nvidia is not None
    assert "GeForce RTX 3050" in nvidia.model
    assert nvidia.pci_id == "01:00.0"
    assert "3D controller" in nvidia.controller_type


def test_parse_lspci_amd():
    devices = _parse_lspci_text(MOCK_LSPCI_AMD)
    assert len(devices) == 1
    assert "Advanced Micro Devices" in devices[0].vendor or "AMD" in devices[0].vendor
    assert "Radeon" in devices[0].model


@patch("app.tools.gpu.execute_command")
def test_inspect_gpu_missing_lspci(mock_exec):
    mock_exec.return_value = (127, "", "lspci: command not found")
    gpu = inspect_gpu()
    assert gpu.count == 0
    assert gpu.error is not None
    assert "pciutils" in gpu.error

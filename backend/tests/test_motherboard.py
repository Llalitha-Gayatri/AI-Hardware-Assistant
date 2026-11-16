"""Unit tests for Motherboard, BIOS, and Memory Slot inspection."""
from unittest.mock import patch
from app.tools.motherboard import (
    inspect_motherboard,
    inspect_memory_slots,
    _parse_dmidecode_motherboard,
    _parse_dmidecode_memory,
)
from tests.conftest import MOCK_DMIDECODE_MOTHERBOARD, MOCK_DMIDECODE_MEMORY


def test_parse_dmidecode_motherboard():
    mb = _parse_dmidecode_motherboard(MOCK_DMIDECODE_MOTHERBOARD)
    assert mb.manufacturer == "LENOVO"
    assert mb.product_name == "21CVCTO1WW"
    assert mb.bios_vendor == "LENOVO"
    assert mb.bios_version == "H1ET45WW (1.23 )"
    assert mb.bios_date == "08/10/2023"


def test_parse_dmidecode_memory():
    mem = _parse_dmidecode_memory(MOCK_DMIDECODE_MEMORY)
    assert mem.total_slots == 2
    assert mem.occupied_slots == 1
    assert mem.max_capacity_human == "32 GB"
    assert len(mem.slots) == 2

    slot0 = mem.slots[0]
    assert slot0.size_human == "16 GB"
    assert slot0.type == "DDR4"
    assert slot0.manufacturer == "Samsung"

    slot1 = mem.slots[1]
    assert slot1.size_human == "Empty"


@patch("app.tools.motherboard.execute_command")
def test_inspect_motherboard_permission_denied(mock_exec):
    # Simulates unprivileged user running dmidecode: permission denied (exit code 126)
    mock_exec.return_value = (126, "", "/dev/mem: Permission denied")
    with patch("app.tools.motherboard._read_sysfs_dmi_field", side_effect=lambda f: "Dell Inc." if f == "board_vendor" else None):
        mb = inspect_motherboard()
        assert mb.permission_denied is True
        assert mb.manufacturer == "Dell Inc."
        assert "Root privileges required" in mb.error


@patch("app.tools.motherboard.execute_command")
def test_inspect_memory_slots_permission_denied(mock_exec):
    mock_exec.return_value = (126, "", "Permission denied")
    slots = inspect_memory_slots()
    assert slots.permission_denied is True
    assert "root privileges" in slots.error.lower()
    # Must never invent fake capacities or free slots when permissions are missing
    assert slots.total_slots is None
    assert slots.max_capacity_human is None

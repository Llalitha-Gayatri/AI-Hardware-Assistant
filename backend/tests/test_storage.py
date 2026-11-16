"""Unit tests for storage and disk media classification."""
import json
from unittest.mock import patch
from app.tools.storage import inspect_storage, _classify_media_type, _parse_device_node
from tests.conftest import MOCK_LSBLK_JSON


def test_classify_media_type_rules():
    # 1. NVMe: has tran 'nvme' or name starts with 'nvme'
    assert _classify_media_type("nvme0n1", "nvme", False, "Samsung 980") == "NVMe SSD"
    assert _classify_media_type("nvme0n1", None, False, "Generic") == "NVMe SSD"

    # 2. Rotational drive is always HDD regardless of interface
    assert _classify_media_type("sda", "sata", True, "Seagate Barracuda") == "HDD (Hard Disk Drive)"

    # 3. Non-rotational SATA is SATA SSD
    assert _classify_media_type("sda", "sata", False, "Crucial MX500") == "SATA SSD"

    # 4. Never assume NVMe if bus is SATA or unspecified!
    assert _classify_media_type("sdb", "sata", False, "Fast Drive") != "NVMe SSD"
    assert _classify_media_type("sdc", None, False, "Fast Drive") == "Solid State Drive (SSD)"

    # 5. Unknown when no rotation or model clues exist
    assert _classify_media_type("vda", None, None, "QEMU HARDDISK") == "Unknown"


def test_parse_lsblk_hierarchy():
    data = json.loads(MOCK_LSBLK_JSON)
    devices = [_parse_device_node(d) for d in data["blockdevices"]]

    assert len(devices) == 2

    nvme = next((d for d in devices if d.name == "nvme0n1"), None)
    assert nvme is not None
    assert nvme.media_type == "NVMe SSD"
    assert nvme.children is not None
    assert len(nvme.children) == 2

    # Check root partition mountpoint
    p2 = next((c for c in nvme.children if c.mountpoint == "/"), None)
    assert p2 is not None
    assert p2.filesystem == "ext4"

    hdd = next((d for d in devices if d.name == "sda"), None)
    assert hdd is not None
    assert hdd.media_type == "HDD (Hard Disk Drive)"
    assert hdd.is_rotational is True


@patch("app.tools.storage.execute_command")
def test_inspect_storage_missing_lsblk(mock_exec):
    mock_exec.return_value = (127, "", "lsblk not found")
    st = inspect_storage()
    assert len(st.devices) == 0
    assert st.error is not None
    assert "util-linux" in st.error

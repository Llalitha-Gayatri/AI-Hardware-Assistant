"""Storage hardware inspection tool."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.schemas.hardware import StorageDevice, StorageInfo
from app.tools.base import execute_command, read_sysfs_or_proc_file
from app.tools.ram import format_bytes


def _classify_media_type(
    name: str,
    tran: Optional[str],
    rota: Optional[bool],
    model: Optional[str],
) -> str:
    """
    Carefully classify storage media type based strictly on concrete evidence.
    Rules:
    - Never classify as NVMe unless tran is 'nvme' or device begins with 'nvme'.
    - If rota is True -> HDD.
    - If rota is False and tran is 'sata' -> SATA SSD.
    - If rota is False and tran is 'nvme' -> NVMe SSD.
    - If rota is False and tran is 'usb' -> USB Flash/SSD.
    - If rota is False without known bus -> SSD.
    - If rotational info is absent -> Unknown.
    """
    name_lower = (name or "").lower()
    tran_lower = (tran or "").lower()
    model_lower = (model or "").lower()

    is_nvme = tran_lower == "nvme" or name_lower.startswith("nvme")

    if is_nvme:
        return "NVMe SSD"

    if rota is True:
        return "HDD (Hard Disk Drive)"

    if rota is False:
        if tran_lower in ("sata", "ata"):
            return "SATA SSD"
        elif tran_lower == "usb":
            return "USB Storage"
        elif "ssd" in model_lower:
            return "SSD"
        return "Solid State Drive (SSD)"

    # Fallback to model heuristics only if rota is unknown
    if "ssd" in model_lower:
        return "SSD"
    elif "hdd" in model_lower:
        return "HDD"

    return "Unknown"


def _check_sysfs_rotational(dev_name: str) -> Optional[bool]:
    """Check /sys/block/<dev_name>/queue/rotational."""
    # Strip partition numbers, e.g., sda1 -> sda, nvme0n1p1 -> nvme0n1
    clean_name = dev_name.split("/")[0]
    path = f"/sys/block/{clean_name}/queue/rotational"
    content, err = read_sysfs_or_proc_file(path)
    if content:
        val = content.strip()
        if val == "1":
            return True
        elif val == "0":
            return False
    return None


def _parse_device_node(item: Dict[str, Any]) -> StorageDevice:
    """Recursively parse a block device and its partitions."""
    name = item.get("name", "unknown")
    size_bytes = None
    raw_size = item.get("size")
    if raw_size is not None:
        try:
            size_bytes = int(raw_size)
        except ValueError:
            pass

    size_human = format_bytes(size_bytes) if size_bytes is not None else None
    dev_type = item.get("type", "disk")
    fstype = item.get("fstype")
    mountpoint = item.get("mountpoint")
    model = item.get("model")
    tran = item.get("tran")

    # rota might be bool, string "0"/"1", or None
    rota_raw = item.get("rota")
    rota: Optional[bool] = None
    if isinstance(rota_raw, bool):
        rota = rota_raw
    elif str(rota_raw) in ("1", "true", "True"):
        rota = True
    elif str(rota_raw) in ("0", "false", "False"):
        rota = False
    elif dev_type == "disk":
        # Query sysfs
        rota = _check_sysfs_rotational(name)

    media_type = _classify_media_type(name, tran, rota, model)

    children_list = None
    if "children" in item and isinstance(item["children"], list):
        children_list = [_parse_device_node(child) for child in item["children"]]

    return StorageDevice(
        name=name,
        size_bytes=size_bytes,
        size_human=size_human,
        device_type=dev_type,
        media_type=media_type,
        is_rotational=rota,
        transport=tran,
        filesystem=fstype,
        mountpoint=mountpoint,
        model=model,
        children=children_list,
    )


def inspect_storage() -> StorageInfo:
    """
    Inspect disk storage and partitions using lsblk.
    Returns structured StorageInfo.
    """
    # Try lsblk -J -b -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,ROTA,TRAN,MODEL
    args = [
        "lsblk",
        "-J",
        "-b",
        "-o",
        "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,ROTA,TRAN,MODEL",
    ]
    ret, stdout, stderr = execute_command(args)

    if ret != 0:
        if ret == 127:
            return StorageInfo(
                devices=[],
                error="The 'lsblk' utility is not installed. Storage inspection requires util-linux.",
            )
        return StorageInfo(
            devices=[],
            error=f"Error executing lsblk: {stderr.strip() if stderr else 'command failed'}",
        )

    try:
        data = json.loads(stdout)
        raw_devices = data.get("blockdevices", [])
        devices: List[StorageDevice] = [
            _parse_device_node(d)
            for d in raw_devices
            # Exclude loop devices unless requested to reduce clutter
            if d.get("type") != "loop"
        ]

        total_bytes = sum(
            d.size_bytes or 0
            for d in devices
            if d.device_type == "disk"
        )

        return StorageInfo(
            devices=devices,
            total_storage_bytes=total_bytes if total_bytes > 0 else None,
            raw_source="lsblk (JSON)",
        )

    except json.JSONDecodeError:
        return StorageInfo(
            devices=[],
            error="Failed to parse lsblk JSON output.",
        )

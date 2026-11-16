"""Motherboard, BIOS, and physical memory slots inspection tool using dmidecode and sysfs."""
import re
from typing import List, Optional, Tuple
from app.config import settings
from app.schemas.hardware import MemorySlot, MemorySlotInfo, MotherboardInfo
from app.tools.base import execute_command, read_sysfs_or_proc_file


def _read_sysfs_dmi_field(filename: str) -> Optional[str]:
    """Read a single field from /sys/class/dmi/id/."""
    content, err = read_sysfs_or_proc_file(f"/sys/class/dmi/id/{filename}")
    if content:
        val = content.strip()
        if val and val.lower() not in ("none", "default string", "to be filled by o.e.m."):
            return val
    return None


def _parse_dmidecode_motherboard(stdout: str) -> MotherboardInfo:
    """Parse dmidecode -t baseboard,bios output."""
    m_info = MotherboardInfo(raw_source="dmidecode")
    current_section = None

    for line in stdout.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue

        if "BIOS Information" in line:
            current_section = "bios"
            continue
        elif "Base Board Information" in line or "Baseboard Information" in line:
            current_section = "baseboard"
            continue
        elif not line.startswith("\t") and not line.startswith("    "):
            current_section = None

        if ":" in line_clean and current_section:
            key, val = [p.strip() for p in line_clean.split(":", 1)]
            if current_section == "bios":
                if key == "Vendor":
                    m_info.bios_vendor = val
                elif key == "Version":
                    m_info.bios_version = val
                elif key in ("Release Date", "Date"):
                    m_info.bios_date = val
            elif current_section == "baseboard":
                if key == "Manufacturer":
                    m_info.manufacturer = val
                elif key == "Product Name":
                    m_info.product_name = val
                elif key == "Version":
                    m_info.version = val

    return m_info


def inspect_motherboard() -> MotherboardInfo:
    """
    Inspect motherboard and BIOS details.
    Uses dmidecode if permitted, with transparent fallback to /sys/class/dmi/id.
    """
    if not settings.ALLOW_DMIDECODE:
        return _inspect_motherboard_sysfs(note="dmidecode disabled by configuration.")

    ret, stdout, stderr = execute_command(["dmidecode", "-t", "baseboard,bios"])
    
    if ret == 0 and stdout.strip():
        m_info = _parse_dmidecode_motherboard(stdout)
        if m_info.manufacturer or m_info.product_name or m_info.bios_vendor:
            return m_info

    # Handle permission denied or missing utility: fallback to sysfs
    is_perm_denied = (ret == 126) or ("permission denied" in stderr.lower())
    fallback = _inspect_motherboard_sysfs()
    if is_perm_denied:
        fallback.permission_denied = True
        fallback.error = "Root privileges required for complete dmidecode inspection; reading via sysfs."
    elif ret == 127:
        fallback.error = "The 'dmidecode' utility is not installed; reading via sysfs."
    elif not fallback.manufacturer and not fallback.product_name:
        fallback.error = f"Motherboard info unavailable: {stderr.strip() if stderr else 'unknown error'}"

    return fallback


def _inspect_motherboard_sysfs(note: Optional[str] = None) -> MotherboardInfo:
    """Fallback reader using unprivileged /sys/class/dmi/id virtual files."""
    m = MotherboardInfo(
        manufacturer=_read_sysfs_dmi_field("board_vendor"),
        product_name=_read_sysfs_dmi_field("board_name"),
        version=_read_sysfs_dmi_field("board_version"),
        bios_vendor=_read_sysfs_dmi_field("bios_vendor"),
        bios_version=_read_sysfs_dmi_field("bios_version"),
        bios_date=_read_sysfs_dmi_field("bios_date"),
        raw_source="/sys/class/dmi/id",
        error=note,
    )
    return m


def _parse_dmidecode_memory(stdout: str) -> MemorySlotInfo:
    """Parse dmidecode -t 16,17 memory array and memory device sections."""
    total_slots_dmi: Optional[int] = None
    max_capacity_dmi: Optional[str] = None
    slots: List[MemorySlot] = []

    # Split by Handle blocks
    blocks = re.split(r"\n(?=Handle 0x)", stdout)

    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue

        # Parse Physical Memory Array (Type 16)
        if "Physical Memory Array" in block:
            for l in lines:
                if ":" in l:
                    k, v = [x.strip() for x in l.split(":", 1)]
                    if k == "Maximum Capacity":
                        max_capacity_dmi = v
                    elif k == "Number Of Devices":
                        try:
                            total_slots_dmi = int(v)
                        except ValueError:
                            pass

        # Parse Memory Device (Type 17)
        elif "Memory Device" in block:
            slot_data: dict = {}
            for l in lines:
                if ":" in l:
                    k, v = [x.strip() for x in l.split(":", 1)]
                    slot_data[k] = v

            size_val = slot_data.get("Size", "")
            is_installed = bool(size_val and "no module" not in size_val.lower() and size_val.lower() != "none")

            slots.append(
                MemorySlot(
                    locator=slot_data.get("Locator"),
                    bank_locator=slot_data.get("Bank Locator"),
                    size_human=size_val if is_installed else "Empty",
                    type=slot_data.get("Type") if is_installed else None,
                    speed=slot_data.get("Speed") if is_installed else None,
                    manufacturer=slot_data.get("Manufacturer") if is_installed else None,
                    part_number=slot_data.get("Part Number") if is_installed else None,
                )
            )

    occupied = len([s for s in slots if s.size_human and s.size_human != "Empty"])
    total_slots = total_slots_dmi if total_slots_dmi is not None else len(slots)

    return MemorySlotInfo(
        total_slots=total_slots if total_slots > 0 else None,
        occupied_slots=occupied,
        max_capacity_human=max_capacity_dmi,
        slots=slots,
        raw_source="dmidecode -t 16,17",
    )


def inspect_memory_slots() -> MemorySlotInfo:
    """
    Inspect physical memory slots and RAM upgradeability using dmidecode.
    Strictly reports only verified motherboard information without guessing.
    """
    if not settings.ALLOW_DMIDECODE:
        return MemorySlotInfo(
            permission_denied=True,
            error="dmidecode execution is disabled by configuration.",
        )

    ret, stdout, stderr = execute_command(["dmidecode", "-t", "16,17"])

    if ret == 0 and stdout.strip():
        parsed = _parse_dmidecode_memory(stdout)
        if parsed.total_slots is not None or parsed.slots:
            return parsed

    # Missing permissions or utility
    is_perm_denied = (ret == 126) or ("permission denied" in stderr.lower())
    if is_perm_denied:
        return MemorySlotInfo(
            permission_denied=True,
            error="Permission denied: dmidecode requires root privileges to read DMI physical memory slots.",
        )
    elif ret == 127:
        return MemorySlotInfo(
            error="The 'dmidecode' utility is not installed on this system.",
        )

    return MemorySlotInfo(
        error=f"Could not read memory slot information: {stderr.strip() if stderr else 'unknown error'}"
    )

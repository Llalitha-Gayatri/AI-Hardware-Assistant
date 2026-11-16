"""GPU hardware inspection tool."""
import re
from typing import List, Tuple
from app.schemas.hardware import GPUDevice, GPUInfo
from app.tools.base import execute_command


KNOWN_VENDORS = [
    "NVIDIA Corporation",
    "NVIDIA",
    "Intel Corporation",
    "Intel",
    "Advanced Micro Devices, Inc.",
    "AMD",
    "ATI Technologies Inc",
    "Qualcomm",
    "Apple",
    "VMware",
    "Red Hat, Inc.",
    "VirtualBox",
]


def _extract_vendor_and_model(full_str: str) -> Tuple[str, str]:
    """Extract vendor name and clean model string."""
    clean_str = re.sub(r"\(rev [a-f0-9]+\)", "", full_str, flags=re.IGNORECASE).strip()

    detected_vendor = "Unknown"
    for v in KNOWN_VENDORS:
        if v.lower() in clean_str.lower():
            detected_vendor = v
            break

    # Strip bracketed abbreviations if present, but keep clean text
    return detected_vendor, clean_str


def _parse_lspci_text(stdout: str) -> List[GPUDevice]:
    """Parse output from lspci for VGA, 3D, and Display controllers."""
    devices: List[GPUDevice] = []
    gpu_keywords = ("vga compatible controller", "3d controller", "display controller")

    for line in stdout.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue

        lower_line = line_clean.lower()
        matched_kw = next((kw for kw in gpu_keywords if kw in lower_line), None)
        if not matched_kw:
            continue

        # Format: 01:00.0 3D controller: NVIDIA Corporation GA107M [GeForce RTX 3050 Mobile] (rev a1)
        # Match PCI address and controller description
        match = re.match(r"^([0-9a-fA-F:\.]+)\s+([^:]+):\s+(.*)$", line_clean)
        if match:
            pci_id = match.group(1).strip()
            ctrl_type = match.group(2).strip()
            desc = match.group(3).strip()
            vendor, model = _extract_vendor_and_model(desc)
            devices.append(
                GPUDevice(
                    vendor=vendor,
                    model=model,
                    pci_id=pci_id,
                    controller_type=ctrl_type,
                )
            )
        else:
            # Fallback split
            parts = line_clean.split(":", 2)
            if len(parts) >= 3:
                pci_id = parts[0].split()[0] if parts[0].split() else None
                vendor, model = _extract_vendor_and_model(parts[2].strip())
                devices.append(
                    GPUDevice(
                        vendor=vendor,
                        model=model,
                        pci_id=pci_id,
                        controller_type="Graphics Controller",
                    )
                )

    return devices


def inspect_gpu() -> GPUInfo:
    """
    Inspect graphics hardware using lspci.
    Returns structured GPUInfo.
    """
    ret, stdout, stderr = execute_command(["lspci"])
    if ret != 0:
        if ret == 127:
            return GPUInfo(
                devices=[],
                count=0,
                error="The 'lspci' utility is not installed. Run 'sudo apt install pciutils' to enable GPU inspection.",
            )
        return GPUInfo(
            devices=[],
            count=0,
            error=f"Error running lspci: {stderr.strip() if stderr else 'command failed'}",
        )

    devices = _parse_lspci_text(stdout)
    return GPUInfo(
        devices=devices,
        count=len(devices),
        raw_source="lspci",
        error=None if devices else "No graphics controllers (VGA/3D/Display) were found on PCI bus.",
    )

"""Host system environment and WSL2 detector."""
import os
import platform
from pathlib import Path
from typing import Optional
from app.schemas.hardware import SystemEnvironment


def detect_environment() -> SystemEnvironment:
    """
    Detect operating system details, kernel, and WSL2 environment caveats.
    """
    is_linux = platform.system().lower() == "linux"
    kernel_version = platform.release()
    is_wsl2 = False
    distro_name = "Unknown Linux Distribution"
    warning: Optional[str] = None

    # Check WSL environment variables
    if os.getenv("WSL_DISTRO_NAME") or os.getenv("WSL_INTEROP"):
        is_wsl2 = True

    # Check /proc/version
    proc_version_path = Path("/proc/version")
    if proc_version_path.exists():
        try:
            with open(proc_version_path, "r", encoding="utf-8", errors="ignore") as f:
                vcontent = f.read().lower()
                if "microsoft" in vcontent or "wsl" in vcontent:
                    is_wsl2 = True
        except Exception:
            pass

    # Read distro information from /etc/os-release
    os_release_path = Path("/etc/os-release")
    if os_release_path.exists():
        try:
            with open(os_release_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        distro_name = line.strip().split("=", 1)[1].strip('"\'')
                        break
        except Exception:
            pass
    elif not is_linux:
        distro_name = f"{platform.system()} {platform.release()}"

    if is_wsl2:
        warning = (
            "Running inside Windows Subsystem for Linux (WSL2). "
            "Physical motherboard BIOS, DMI tables, and direct PCIe hardware access "
            "are abstracted or virtualized by the Windows hypervisor."
        )
    elif not is_linux:
        warning = (
            f"Host is running on {platform.system()}. "
            "Native Linux utilities (lscpu, free, lspci, lsblk, dmidecode) are simulated or unavailable."
        )

    return SystemEnvironment(
        is_linux=is_linux,
        is_wsl2=is_wsl2,
        distro_name=distro_name,
        kernel_version=kernel_version,
        warning=warning,
    )

"""RAM hardware inspection tool."""
import re
from typing import Dict, Optional
from app.schemas.hardware import RAMInfo
from app.tools.base import execute_command, read_sysfs_or_proc_file


def format_bytes(num_bytes: int) -> str:
    """Format bytes into readable string (GB/MB)."""
    if num_bytes >= 1024**3:
        return f"{num_bytes / (1024**3):.2f} GB"
    elif num_bytes >= 1024**2:
        return f"{num_bytes / (1024**2):.2f} MB"
    elif num_bytes >= 1024:
        return f"{num_bytes / 1024:.2f} KB"
    return f"{num_bytes} B"


def _parse_meminfo(content: str) -> RAMInfo:
    """Parse /proc/meminfo content."""
    items: Dict[str, int] = {}
    for line in content.splitlines():
        parts = line.split(":")
        if len(parts) == 2:
            key = parts[0].strip()
            # Value usually in kB: '16180520 kB'
            val_match = re.match(r"^(\d+)", parts[1].strip())
            if val_match:
                items[key] = int(val_match.group(1)) * 1024  # convert kB to bytes

    total = items.get("MemTotal")
    if not total:
        return RAMInfo(error="MemTotal missing from /proc/meminfo")

    available = items.get("MemAvailable")
    free = items.get("MemFree", 0)

    # If MemAvailable is absent (older Linux kernels), approximate using free + buffers + cached
    if available is None:
        buffers = items.get("Buffers", 0)
        cached = items.get("Cached", 0)
        available = free + buffers + cached

    used = max(0, total - available)
    usage_pct = round((used / total) * 100, 1) if total > 0 else 0.0

    return RAMInfo(
        total_bytes=total,
        used_bytes=used,
        available_bytes=available,
        free_bytes=free,
        usage_percentage=usage_pct,
        total_human=format_bytes(total),
        used_human=format_bytes(used),
        available_human=format_bytes(available),
        raw_source="/proc/meminfo",
    )


def _parse_free_bytes(stdout: str) -> Optional[RAMInfo]:
    """Parse stdout of 'free -b'."""
    lines = stdout.strip().splitlines()
    for line in lines:
        if line.startswith("Mem:") or line.startswith("Memory:"):
            parts = line.split()
            # Format: Mem: total used free shared buff/cache available
            if len(parts) >= 7:
                try:
                    total = int(parts[1])
                    used = int(parts[2])
                    free = int(parts[3])
                    available = int(parts[6])
                    usage_pct = round((used / total) * 100, 1) if total > 0 else 0.0
                    return RAMInfo(
                        total_bytes=total,
                        used_bytes=used,
                        available_bytes=available,
                        free_bytes=free,
                        usage_percentage=usage_pct,
                        total_human=format_bytes(total),
                        used_human=format_bytes(used),
                        available_human=format_bytes(available),
                        raw_source="free -b",
                    )
                except (ValueError, IndexError):
                    break
    return None


def inspect_ram() -> RAMInfo:
    """
    Inspect system RAM using free command with fallback to /proc/meminfo.
    Returns structured RAMInfo.
    """
    # 1. Try 'free -b'
    ret, stdout, stderr = execute_command(["free", "-b"])
    if ret == 0 and stdout:
        parsed = _parse_free_bytes(stdout)
        if parsed:
            return parsed

    # 2. Fallback to /proc/meminfo
    content, err = read_sysfs_or_proc_file("/proc/meminfo")
    if content:
        return _parse_meminfo(content)

    return RAMInfo(
        error=f"Could not inspect RAM. free: {stderr.strip() if stderr else 'not available'}; /proc/meminfo: {err}"
    )

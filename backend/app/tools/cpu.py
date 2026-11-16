"""CPU hardware inspection tool."""
import json
import re
from typing import Dict, Optional, Tuple
from app.schemas.hardware import CPUInfo
from app.tools.base import execute_command, read_sysfs_or_proc_file


def _parse_lscpu_json(data: dict) -> CPUInfo:
    """Parse output from 'lscpu -J'."""
    items: Dict[str, str] = {}
    for entry in data.get("lscpu", []):
        field = entry.get("field", "").rstrip(":")
        val = entry.get("data")
        if field and val is not None:
            items[field.strip()] = str(val).strip()

    model = items.get("Model name") or items.get("Processor") or "Unknown"
    arch = items.get("Architecture") or "Unknown"

    threads = None
    if "CPU(s)" in items:
        try:
            threads = int(items["CPU(s)"])
        except ValueError:
            pass

    cores = None
    if "Core(s) per socket" in items and "Socket(s)" in items:
        try:
            cores = int(items["Core(s) per socket"]) * int(items["Socket(s)"])
        except ValueError:
            pass
    elif "Core(s) per cluster" in items and "Socket(s)" in items:
        try:
            cores = int(items["Core(s) per cluster"]) * int(items["Socket(s)"])
        except ValueError:
            pass

    freq_mhz = None
    if "CPU MHz" in items:
        try:
            freq_mhz = float(items["CPU MHz"])
        except ValueError:
            pass

    min_freq = None
    if "CPU min MHz" in items:
        try:
            min_freq = float(items["CPU min MHz"])
        except ValueError:
            pass

    max_freq = None
    if "CPU max MHz" in items:
        try:
            max_freq = float(items["CPU max MHz"])
        except ValueError:
            pass

    virt = items.get("Virtualization") or items.get("Hypervisor vendor")

    return CPUInfo(
        model=model,
        architecture=arch,
        cores=cores,
        threads=threads,
        frequency_mhz=freq_mhz,
        min_frequency_mhz=min_freq,
        max_frequency_mhz=max_freq,
        virtualization=virt,
        raw_source="lscpu (JSON)",
    )


def _parse_lscpu_text(text: str) -> CPUInfo:
    """Parse traditional colon-delimited 'lscpu' output."""
    items: Dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            items[key.strip()] = val.strip()

    model = items.get("Model name") or items.get("Processor") or "Unknown"
    arch = items.get("Architecture") or "Unknown"

    threads = None
    if "CPU(s)" in items:
        try:
            threads = int(items["CPU(s)"])
        except ValueError:
            pass

    cores = None
    if "Core(s) per socket" in items and "Socket(s)" in items:
        try:
            cores = int(items["Core(s) per socket"]) * int(items["Socket(s)"])
        except ValueError:
            pass

    freq_mhz = None
    if "CPU MHz" in items:
        try:
            freq_mhz = float(items["CPU MHz"])
        except ValueError:
            pass

    min_freq = None
    if "CPU min MHz" in items:
        try:
            min_freq = float(items["CPU min MHz"])
        except ValueError:
            pass

    max_freq = None
    if "CPU max MHz" in items:
        try:
            max_freq = float(items["CPU max MHz"])
        except ValueError:
            pass

    virt = items.get("Virtualization") or items.get("Hypervisor vendor")

    return CPUInfo(
        model=model,
        architecture=arch,
        cores=cores,
        threads=threads,
        frequency_mhz=freq_mhz,
        min_frequency_mhz=min_freq,
        max_frequency_mhz=max_freq,
        virtualization=virt,
        raw_source="lscpu (text)",
    )


def _parse_proc_cpuinfo(content: str) -> CPUInfo:
    """Fallback parser using Linux /proc/cpuinfo."""
    processors = content.strip().split("\n\n")
    if not processors or not processors[0].strip():
        return CPUInfo(model="Unknown", architecture="Unknown", error="Empty /proc/cpuinfo")

    first_block = processors[0]
    items: Dict[str, str] = {}
    for line in first_block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            items[k.strip()] = v.strip()

    model = items.get("model name") or items.get("Processor") or "Unknown"
    threads = len([p for p in processors if "processor" in p]) or None
    
    cores = None
    if "cpu cores" in items:
        try:
            cores = int(items["cpu cores"])
        except ValueError:
            pass

    freq_mhz = None
    if "cpu MHz" in items:
        try:
            freq_mhz = float(items["cpu MHz"])
        except ValueError:
            pass

    flags = items.get("flags", "").split()
    virt = None
    if "vmx" in flags:
        virt = "VT-x (Intel)"
    elif "svm" in flags:
        virt = "AMD-V (AMD)"

    return CPUInfo(
        model=model,
        architecture="x86_64" if "lm" in flags else "Unknown",
        cores=cores,
        threads=threads,
        frequency_mhz=freq_mhz,
        virtualization=virt,
        raw_source="/proc/cpuinfo",
    )


def inspect_cpu() -> CPUInfo:
    """
    Inspect CPU hardware using lscpu with fallback to /proc/cpuinfo.
    Returns structured CPUInfo.
    """
    # 1. Try lscpu -J
    ret, stdout, stderr = execute_command(["lscpu", "-J"])
    if ret == 0 and stdout.strip():
        try:
            data = json.loads(stdout)
            return _parse_lscpu_json(data)
        except Exception:
            pass

    # 2. Try lscpu (plain text)
    ret, stdout, stderr = execute_command(["lscpu"])
    if ret == 0 and stdout.strip():
        return _parse_lscpu_text(stdout)

    # 3. Fallback to /proc/cpuinfo
    content, err = read_sysfs_or_proc_file("/proc/cpuinfo")
    if content:
        return _parse_proc_cpuinfo(content)

    return CPUInfo(
        model="Unknown",
        architecture="Unknown",
        error=f"Could not inspect CPU. lscpu: {stderr.strip() if stderr else 'not available'}; /proc/cpuinfo: {err}",
    )

"""Pydantic schemas for structured hardware inspection models."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class SystemEnvironment(BaseModel):
    """Host environment details, including WSL2 detection."""
    is_linux: bool = True
    is_wsl2: bool = False
    distro_name: Optional[str] = None
    kernel_version: Optional[str] = None
    warning: Optional[str] = None


class CPUInfo(BaseModel):
    """CPU specifications and state."""
    model: str = "Unknown"
    architecture: str = "Unknown"
    cores: Optional[int] = None
    threads: Optional[int] = None
    frequency_mhz: Optional[float] = None
    min_frequency_mhz: Optional[float] = None
    max_frequency_mhz: Optional[float] = None
    virtualization: Optional[str] = None
    raw_source: str = "lscpu"
    error: Optional[str] = None


class RAMInfo(BaseModel):
    """System memory utilization and totals."""
    total_bytes: Optional[int] = None
    used_bytes: Optional[int] = None
    available_bytes: Optional[int] = None
    free_bytes: Optional[int] = None
    usage_percentage: Optional[float] = None
    total_human: Optional[str] = None
    used_human: Optional[str] = None
    available_human: Optional[str] = None
    raw_source: str = "free / /proc/meminfo"
    error: Optional[str] = None


class GPUDevice(BaseModel):
    """Individual GPU device detected on the PCI bus or DRM."""
    vendor: str = "Unknown"
    model: str = "Unknown"
    pci_id: Optional[str] = None
    controller_type: str = "VGA compatible controller"


class GPUInfo(BaseModel):
    """Collection of detected GPUs."""
    devices: List[GPUDevice] = Field(default_factory=list)
    count: int = 0
    raw_source: str = "lspci"
    error: Optional[str] = None


class StorageDevice(BaseModel):
    """Block device or partition details."""
    name: str
    size_bytes: Optional[int] = None
    size_human: Optional[str] = None
    device_type: str = "disk"  # disk, part, rom, etc.
    media_type: str = "Unknown"  # NVMe, SATA SSD, HDD, Unknown
    is_rotational: Optional[bool] = None
    transport: Optional[str] = None  # nvme, sata, usb, etc.
    filesystem: Optional[str] = None
    mountpoint: Optional[str] = None
    model: Optional[str] = None
    children: Optional[List[StorageDevice]] = None


class StorageInfo(BaseModel):
    """Storage devices breakdown."""
    devices: List[StorageDevice] = Field(default_factory=list)
    total_storage_bytes: Optional[int] = None
    raw_source: str = "lsblk"
    error: Optional[str] = None


class MemorySlot(BaseModel):
    """Individual DMI physical memory slot."""
    locator: Optional[str] = None
    bank_locator: Optional[str] = None
    size_human: Optional[str] = None
    type: Optional[str] = None
    speed: Optional[str] = None
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None


class MemorySlotInfo(BaseModel):
    """Memory slot configuration and motherboard limits."""
    total_slots: Optional[int] = None
    occupied_slots: Optional[int] = None
    max_capacity_human: Optional[str] = None
    slots: List[MemorySlot] = Field(default_factory=list)
    permission_denied: bool = False
    raw_source: str = "dmidecode"
    error: Optional[str] = None


class MotherboardInfo(BaseModel):
    """Motherboard and BIOS data."""
    manufacturer: Optional[str] = None
    product_name: Optional[str] = None
    version: Optional[str] = None
    bios_vendor: Optional[str] = None
    bios_version: Optional[str] = None
    bios_date: Optional[str] = None
    permission_denied: bool = False
    raw_source: str = "dmidecode / sysfs"
    error: Optional[str] = None


class HardwareSummary(BaseModel):
    """Aggregated full system hardware snapshot."""
    environment: SystemEnvironment
    cpu: CPUInfo
    ram: RAMInfo
    gpu: GPUInfo
    storage: StorageInfo
    motherboard: MotherboardInfo
    memory_slots: MemorySlotInfo

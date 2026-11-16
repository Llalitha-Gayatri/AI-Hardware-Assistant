"""Hardware service aggregating system inspection data."""
from app.schemas.hardware import (
    CPUInfo,
    GPUInfo,
    HardwareSummary,
    MemorySlotInfo,
    MotherboardInfo,
    RAMInfo,
    StorageInfo,
    SystemEnvironment,
)
from app.tools.cpu import inspect_cpu
from app.tools.environment import detect_environment
from app.tools.gpu import inspect_gpu
from app.tools.motherboard import inspect_memory_slots, inspect_motherboard
from app.tools.ram import inspect_ram
from app.tools.storage import inspect_storage


class HardwareService:
    """Service to collect and serve validated hardware details."""

    @staticmethod
    def get_cpu() -> CPUInfo:
        return inspect_cpu()

    @staticmethod
    def get_ram() -> RAMInfo:
        return inspect_ram()

    @staticmethod
    def get_gpu() -> GPUInfo:
        return inspect_gpu()

    @staticmethod
    def get_storage() -> StorageInfo:
        return inspect_storage()

    @staticmethod
    def get_motherboard() -> MotherboardInfo:
        return inspect_motherboard()

    @staticmethod
    def get_memory_slots() -> MemorySlotInfo:
        return inspect_memory_slots()

    @staticmethod
    def get_environment() -> SystemEnvironment:
        return detect_environment()

    @classmethod
    def get_full_summary(cls) -> HardwareSummary:
        """Collect a full snapshot across all subsystems."""
        return HardwareSummary(
            environment=cls.get_environment(),
            cpu=cls.get_cpu(),
            ram=cls.get_ram(),
            gpu=cls.get_gpu(),
            storage=cls.get_storage(),
            motherboard=cls.get_motherboard(),
            memory_slots=cls.get_memory_slots(),
        )


hardware_service = HardwareService()

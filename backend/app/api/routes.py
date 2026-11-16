"""API Routes for hardware inspection and AI chat."""
from fastapi import APIRouter, HTTPException, status
from app.ai.agent import hardware_agent
from app.config import settings
from app.schemas.chat import ChatRequest, ChatResponse
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
from app.services.hardware_service import hardware_service

router = APIRouter(prefix="/api", tags=["Hardware & AI Assistant"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint to verify backend status."""
    return {
        "status": "healthy",
        "service": "AI Hardware Assistant",
        "llm_provider": settings.LLM_PROVIDER,
        "environment": hardware_service.get_environment().model_dump(),
    }


@router.get("/hardware", response_model=HardwareSummary)
def get_hardware_summary():
    """Return aggregated hardware overview across all subsystems."""
    try:
        return hardware_service.get_full_summary()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to inspect system hardware: {str(exc)}",
        )


@router.get("/hardware/cpu", response_model=CPUInfo)
def get_cpu_info():
    """Return CPU specifications and frequencies."""
    return hardware_service.get_cpu()


@router.get("/hardware/ram", response_model=RAMInfo)
def get_ram_info():
    """Return system RAM usage and capacity."""
    return hardware_service.get_ram()


@router.get("/hardware/gpu", response_model=GPUInfo)
def get_gpu_info():
    """Return graphics controllers and PCI GPUs."""
    return hardware_service.get_gpu()


@router.get("/hardware/storage", response_model=StorageInfo)
def get_storage_info():
    """Return storage drives, media types, and partitions."""
    return hardware_service.get_storage()


@router.get("/hardware/motherboard", response_model=MotherboardInfo)
def get_motherboard_info():
    """Return motherboard and BIOS details."""
    return hardware_service.get_motherboard()


@router.get("/hardware/memory-slots", response_model=MemorySlotInfo)
def get_memory_slots():
    """Return physical RAM slots, occupancy, and upgrade limit."""
    return hardware_service.get_memory_slots()


@router.get("/hardware/environment", response_model=SystemEnvironment)
def get_environment_info():
    """Return host OS details and WSL2 detection."""
    return hardware_service.get_environment()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """
    Process natural-language hardware query using LLM tool calling.
    Validates tools, executes predefined Linux commands, and returns grounded answer.
    """
    try:
        return await hardware_agent.run(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(exc)}",
        )

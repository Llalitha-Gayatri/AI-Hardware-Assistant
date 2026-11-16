# AI-Powered Hardware Q&A Assistant for Linux - Walkthrough

## Summary of Accomplishments

We have designed, built, tested, and verified the complete **AI-Powered Hardware Q&A Assistant for Linux** in accordance with all interview and production specifications:

1. **System Architecture & Folder Structure**:
   - Organized into a clean, modular structure under `hardware-ai-assistant/` containing `backend/`, `frontend/`, `tests/`, and complete documentation.
   - Built with strict separation of concerns between API routing, hardware inspection, tool registry, and AI agent orchestration.

2. **Security & Zero-Trust Subprocess Execution**:
   - `subprocess.run(..., shell=False, check=False)` with argument lists only. Zero direct shell execution.
   - Strict executable binary allowlist (`lscpu`, `free`, `lspci`, `lsblk`, `dmidecode`, `uname`, `cat`).
   - Strict tool function allowlist in `TOOL_REGISTRY`.
   - Path normalization preventing path traversal (`/etc/shadow`, `/etc/passwd`).
   - Timeouts on all commands to eliminate resource exhaustion and hanging processes.
   - No automatic sudo escalation; unprivileged fallback to `/sys/class/dmi/id/` with clear user messaging.

3. **Accurate Hardware Parsers & Zero-Hallucination Policy**:
   - **CPU**: Inspects `lscpu -J` (JSON) and plain text with fallback to `/proc/cpuinfo`. Extracts model, architecture, cores, threads, clock frequencies, and virtualization flags.
   - **RAM**: Queries `free -b` with fallback to `/proc/meminfo`. Computes accurate usage percentage and human-readable capacity.
   - **GPU**: Uses `lspci` to detect VGA, 3D, and Display controllers, extracting vendors and models.
   - **Storage**: Uses `lsblk` with JSON hierarchy. Accurately distinguishes **NVMe SSD** vs **SATA SSD** vs **HDD** using bus transport and rotational flags (`/sys/block/*/queue/rotational`). Never assumes an SSD is NVMe without evidence.
   - **Motherboard & Memory Slots**: Reads DMI tables via `dmidecode` (and sysfs). Accurately reports memory slots and maximum capacity, refusing to guess if permissions are restricted.
   - **WSL2 Awareness**: Automatically detects when running inside Windows Subsystem for Linux (`/proc/version` and `WSL_DISTRO_NAME`), displaying an alert regarding hypervisor virtualization.

4. **Multi-Turn AI Tool Calling & Pluggable Providers**:
   - Abstract `BaseLLMClient` supporting OpenAI, compatible endpoints (Groq, Ollama, vLLM, DeepSeek), Google Gemini, and a first-class **Mock LLM Provider**.
   - Multi-turn tool calling: Can execute multiple tools for questions requiring multiple subsystems (e.g. `Can I upgrade my RAM to 32 GB?` triggers `inspect_ram` and `inspect_memory_slots`).
   - Grounded conversational follow-ups: Answers queries like `"Is it good for machine learning?"` using previously inspected GPU/RAM facts from conversation history without redundant re-inspection.

5. **REST API**:
   - `GET /api/health`
   - `GET /api/hardware`
   - `GET /api/hardware/cpu`
   - `GET /api/hardware/ram`
   - `GET /api/hardware/gpu`
   - `GET /api/hardware/storage`
   - `GET /api/hardware/motherboard`
   - `GET /api/hardware/memory-slots`
   - `GET /api/hardware/environment`
   - `POST /api/chat`

6. **Frontend Dashboard**:
   - Modern dark/neutral responsive UI.
   - Sidebar displaying live hardware overview cards (CPU, RAM utilization bar, GPU, Storage, Motherboard).
   - WSL2 detection banner.
   - Suggested question chips.
   - User and AI message bubbles with Markdown rendering.
   - Tool execution badges with interactive modal to view raw JSON telemetry.
   - Clear conversation and refresh buttons.

---

## Verification Results

### 1. Pytest Test Suite
Executed 44 comprehensive tests across 9 test modules:

```text
============================= test session starts =============================
collected 44 items

tests/test_agent.py::test_agent_single_tool_call_ram PASSED              [  2%]
tests/test_agent.py::test_agent_multi_tool_call_ram_upgrade PASSED       [  4%]
tests/test_agent.py::test_agent_grounded_upgrade_synthesis PASSED        [  6%]
tests/test_agent.py::test_agent_follow_up_conversation_without_redundant_tools PASSED [  9%]
tests/test_agent.py::test_agent_storage_nvme_question PASSED             [ 11%]
tests/test_agent.py::test_wsl2_environment_detection PASSED              [ 13%]
tests/test_api.py::test_serve_index_html PASSED                          [ 15%]
tests/test_api.py::test_get_health PASSED                                [ 18%]
tests/test_api.py::test_get_hardware_summary PASSED                      [ 20%]
tests/test_api.py::test_get_cpu_endpoint PASSED                          [ 22%]
tests/test_api.py::test_get_ram_endpoint PASSED                          [ 25%]
tests/test_api.py::test_get_gpu_endpoint PASSED                          [ 27%]
tests/test_api.py::test_get_storage_endpoint PASSED                      [ 29%]
tests/test_api.py::test_get_motherboard_endpoint PASSED                  [ 31%]
tests/test_api.py::test_get_memory_slots_endpoint PASSED                 [ 34%]
tests/test_api.py::test_get_environment_endpoint PASSED                  [ 36%]
tests/test_api.py::test_post_chat_endpoint PASSED                        [ 38%]
tests/test_api.py::test_post_chat_invalid_empty_body PASSED              [ 40%]
tests/test_cpu.py::test_parse_lscpu_json PASSED                          [ 43%]
tests/test_cpu.py::test_parse_lscpu_text PASSED                          [ 45%]
tests/test_cpu.py::test_parse_proc_cpuinfo PASSED                        [ 47%]
tests/test_cpu.py::test_inspect_cpu_missing_utility PASSED               [ 50%]
tests/test_gpu.py::test_parse_lspci_dual_gpu PASSED                      [ 52%]
tests/test_gpu.py::test_parse_lspci_amd PASSED                           [ 54%]
tests/test_gpu.py::test_inspect_gpu_missing_lspci PASSED                 [ 56%]
tests/test_motherboard.py::test_parse_dmidecode_motherboard PASSED       [ 59%]
tests/test_motherboard.py::test_parse_dmidecode_memory PASSED            [ 61%]
tests/test_motherboard.py::test_inspect_motherboard_permission_denied PASSED [ 63%]
tests/test_motherboard.py::test_inspect_memory_slots_permission_denied PASSED [ 65%]
tests/test_ram.py::test_format_bytes PASSED                              [ 68%]
tests/test_ram.py::test_parse_free_bytes PASSED                          [ 70%]
tests/test_ram.py::test_parse_meminfo PASSED                             [ 72%]
tests/test_ram.py::test_inspect_ram_fallback_to_meminfo PASSED           [ 75%]
tests/test_real_llm.py::test_get_llm_client_returns_openai_when_configured PASSED [ 77%]
tests/test_real_llm.py::test_get_llm_client_falls_back_to_mock_when_key_empty PASSED [ 79%]
tests/test_real_llm.py::test_real_llm_tool_calling_workflow_with_openai_client PASSED [ 81%]
tests/test_registry_security.py::test_registry_allowlist_enforcement PASSED [ 84%]
tests/test_registry_security.py::test_execute_command_rejects_unallowlisted_binaries PASSED [ 86%]
tests/test_registry_security.py::test_execute_command_rejects_empty_or_non_list PASSED [ 88%]
tests/test_registry_security.py::test_read_sysfs_blocks_path_traversal PASSED [ 90%]
tests/test_registry_security.py::test_available_tools_schema_format PASSED [ 93%]
tests/test_storage.py::test_classify_media_type_rules PASSED             [ 95%]
tests/test_storage.py::test_parse_lsblk_hierarchy PASSED                 [ 97%]
tests/test_storage.py::test_inspect_storage_missing_lsblk PASSED         [100%]

======================== 44 passed, 1 warning in 1.50s ========================
```

### 2. End-to-End Verification (`verify_e2e.py`)
- Verified `GET /api/health` returns healthy and reports system environment.
- Verified `GET /api/hardware` aggregates all telemetry cleanly.
- Verified single-tool query (`inspect_ram`).
- Verified multi-tool query (`inspect_ram` + `inspect_memory_slots`).
- Verified conversational follow-up regarding ML readiness grounded in detected hardware.
- Verified static frontend HTML serving from FastAPI root (`/`).

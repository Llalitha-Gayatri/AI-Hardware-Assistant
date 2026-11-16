"""Security and allowlist enforcement tests."""
import pytest
from app.tools.base import execute_command, read_sysfs_or_proc_file
from app.tools.registry import execute_tool, is_tool_allowed, get_available_tools_schema


def test_registry_allowlist_enforcement():
    # Legitimate registered tools
    assert is_tool_allowed("inspect_cpu") is True
    assert is_tool_allowed("inspect_ram") is True
    assert is_tool_allowed("inspect_gpu") is True
    assert is_tool_allowed("inspect_storage") is True
    assert is_tool_allowed("inspect_motherboard") is True
    assert is_tool_allowed("inspect_memory_slots") is True
    assert is_tool_allowed("inspect_environment") is True

    # Malicious or unregistered tools must be rejected immediately
    assert is_tool_allowed("rm") is False
    assert is_tool_allowed("bash") is False
    assert is_tool_allowed("execute_arbitrary_shell") is False
    assert is_tool_allowed("download_payload") is False

    res = execute_tool("unregistered_malicious_tool")
    assert res.success is False
    assert "Security violation" in res.error


def test_execute_command_rejects_unallowlisted_binaries():
    # Calling unauthorized binaries raises PermissionError immediately
    with pytest.raises(PermissionError) as exc_info:
        execute_command(["rm", "-rf", "/tmp/test"])
    assert "not in the security allowlist" in str(exc_info.value)

    with pytest.raises(PermissionError):
        execute_command(["bash", "-c", "echo pwned"])

    with pytest.raises(PermissionError):
        execute_command(["curl", "https://attacker.com"])


def test_execute_command_rejects_empty_or_non_list():
    with pytest.raises(ValueError):
        execute_command([])


def test_read_sysfs_blocks_path_traversal():
    # Attacking with path traversal or sensitive files outside proc/sys
    content, err = read_sysfs_or_proc_file("/etc/shadow")
    assert content is None
    assert "restricted by file security policy" in err

    content, err = read_sysfs_or_proc_file("/proc/cpuinfo/../../etc/passwd")
    # Normalized path is /etc/passwd which is blocked
    assert content is None
    assert "restricted by file security policy" in err


def test_available_tools_schema_format():
    schemas = get_available_tools_schema()
    assert len(schemas) >= 6
    for s in schemas:
        assert s["type"] == "function"
        assert "name" in s["function"]
        assert "description" in s["function"]

"""Base execution utilities for secure hardware inspection."""
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from app.config import settings

# Strict allowlist of Linux executable binaries permitted to be run
ALLOWED_BINARIES = frozenset([
    "lscpu",
    "free",
    "lspci",
    "lsblk",
    "dmidecode",
    "uname",
    "cat",
])

# Permitted prefixes for direct sysfs / procfs virtual file reads
ALLOWED_FILE_PREFIXES = (
    "/proc/cpuinfo",
    "/proc/meminfo",
    "/proc/version",
    "/sys/class/dmi/id/",
    "/sys/block/",
    "/sys/class/drm/",
    "/etc/os-release",
)


class CommandExecutionError(Exception):
    """Raised when command execution fails unexpectedly."""
    pass


def execute_command(
    command_args: List[str],
    timeout: Optional[int] = None,
) -> Tuple[int, str, str]:
    """
    Safely execute a predefined command with arguments without a shell.
    
    Security controls:
    1. Only argument lists are accepted (no shell strings).
    2. shell=False is strictly enforced.
    3. Binary must be present in ALLOWED_BINARIES.
    4. Execution timeout prevents hangs or DoS.
    5. Missing utilities and permission errors return clean exit codes/messages.
    
    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    if not command_args or not isinstance(command_args, list):
        raise ValueError("command_args must be a non-empty list of strings")

    binary = command_args[0]
    # Strip any directory path to verify the pure binary name
    binary_name = Path(binary).name

    if binary_name not in ALLOWED_BINARIES:
        raise PermissionError(
            f"Execution rejected: binary '{binary_name}' is not in the security allowlist."
        )

    # Check if executable exists in PATH
    if shutil.which(binary) is None:
        return (
            127,
            "",
            f"Utility '{binary_name}' is not installed or not found in system PATH.",
        )

    timeout_seconds = timeout or settings.COMMAND_TIMEOUT_SECONDS

    try:
        process = subprocess.run(
            command_args,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return process.returncode, process.stdout, process.stderr

    except subprocess.TimeoutExpired:
        return (
            124,
            "",
            f"Command '{' '.join(command_args)}' timed out after {timeout_seconds}s.",
        )
    except PermissionError:
        return (
            126,
            "",
            f"Permission denied executing '{binary_name}'. Elevated permissions may be required.",
        )
    except Exception as exc:
        return (
            1,
            "",
            f"Unexpected error running '{binary_name}': {str(exc)}",
        )


def read_sysfs_or_proc_file(path_str: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Safely read virtual files from /proc or /sys.
    
    Security controls:
    1. Checks path against ALLOWED_FILE_PREFIXES.
    2. Path traversal (e.g. '../') is blocked by normalizing path.
    3. Read-only operation.
    
    Returns:
        Tuple of (content_or_None, error_or_None)
    """
    try:
        norm_path = os.path.normpath(path_str)
        # Normalize slashes for Linux paths
        posix_norm = norm_path.replace("\\", "/")

        # Security check: must start with an allowed prefix
        if not any(posix_norm.startswith(prefix) for prefix in ALLOWED_FILE_PREFIXES):
            return None, f"Access to '{posix_norm}' is restricted by file security policy."

        path_obj = Path(norm_path)
        if not path_obj.exists():
            return None, f"File '{norm_path}' not found."

        if not path_obj.is_file():
            return None, f"Path '{norm_path}' is not a regular file."

        # Read content with limit to prevent memory exhaustion
        with open(path_obj, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(131072)  # Max 128KB
        return content, None

    except PermissionError:
        return None, f"Permission denied accessing '{path_str}'."
    except Exception as exc:
        return None, f"Error reading '{path_str}': {str(exc)}"

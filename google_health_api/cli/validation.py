"""Input validation and dry-run mechanism for Google Health CLI."""

import os
import sys
import json
from typing import Any


def validate_resource_name(name: str) -> None:
    """Validate resource name/IDs to prevent control character injection, double encoding, or path traversal.

    Args:
        name: The resource name or identifier to validate.

    Raises:
        ValueError: If validation fails.
    """
    if not name:
        return

    # Reject control characters (ASCII < 0x20)
    if any(ord(c) < 32 for c in name):
        raise ValueError("Resource identifier contains control characters.")

    # Reject suspected query injection, escaping, or URL manipulation characters
    forbidden_chars = ["?", "#", "%"]
    if any(c in name for c in forbidden_chars):
        raise ValueError(
            f"Resource identifier contains forbidden characters: {forbidden_chars}."
        )

    # Reject path traversal patterns
    if ".." in name or "\\" in name:
        raise ValueError("Resource identifier cannot contain path traversal patterns.")


def validate_safe_path(path: str) -> None:
    """Prevent path traversal vulnerabilities by enforcing that file reads/writes are sandboxed to safe directories.

    Args:
        path: File path to check.

    Raises:
        ValueError: If the resolved path is outside the safe sandboxed directory.
    """
    if not path:
        return

    # Reject obvious traversal sequences
    if ".." in path:
        raise ValueError("Path traversal sequence '..' is forbidden.")

    cwd = os.path.abspath(os.getcwd())
    abs_path = os.path.abspath(path)

    # Check if the absolute path falls outside the current working directory
    if not abs_path.startswith(cwd):
        raise ValueError(
            f"Path '{path}' resolves to '{abs_path}', which falls outside the sandboxed directory '{cwd}'."
        )


def check_dry_run(dry_run: bool, method: str, url: str, payload: Any = None) -> None:
    """Exit early printing JSON dry-run details if dry-run flag is active.

    Args:
        dry_run: True if dry-run mode is enabled.
        method: HTTP method (e.g. POST, PATCH, DELETE).
        url: Request path.
        payload: Optional request payload.
    """
    if not dry_run:
        return

    result = {
        "dry_run": True,
        "method": method,
        "url": url,
        "payload": payload,
    }
    print(json.dumps(result, indent=2))
    sys.exit(0)

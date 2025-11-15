"""
Credential Retrieval Adapters

This package contains adapters for retrieving credentials from various sources:
- SSH: Remote Linux/Unix systems via SSH
- SMB: Windows shares and NAS devices
- WinRM: Windows remote management
- Files: Local file system
- API: REST APIs and management interfaces

All adapters implement the BaseAdapter interface defined in base_adapter.py.

Usage:
    from adapters.ssh_adapter import SSHAdapter
    
    adapter = SSHAdapter(config={"timeout_seconds": 30})
    adapter.connect(
        target={"host": "192.168.1.10", "port": 22},
        credentials={"username": "admin", "password": "secret"}
    )
    secret = adapter.retrieve("/etc/app/credentials.conf")
    adapter.cleanup()
"""

__version__ = "1.0.0"
__author__ = "Kiro Team"

from .base_adapter import (
    BaseAdapter,
    AdapterError,
    ConnectionError,
    AuthenticationError,
    RetrievalError,
    EphemeralAccountError
)

__all__ = [
    "BaseAdapter",
    "AdapterError",
    "ConnectionError",
    "AuthenticationError",
    "RetrievalError",
    "EphemeralAccountError"
]

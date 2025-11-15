"""
Per-Subnet Agent Package

This package contains the per-subnet agent implementation for the
Emergency Credential Retrieval System.

The agent runs as a daemon in each network subnet and provides:
- Credential retrieval via multiple adapters
- Local vault for encrypted secret storage
- Token validation and single-use enforcement
- Merkle-stamped audit logging
- HTTPS API with mutual TLS

See agent/DESIGN.md for complete architecture documentation.
"""

__version__ = "1.0.0"
__author__ = "Kiro Team"

from .service import AgentService

__all__ = ["AgentService"]

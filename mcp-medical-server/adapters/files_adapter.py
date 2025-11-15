"""
Files Adapter - Local File System Access

Retrieves credentials from local files (mounted shares, config files, etc.)
Implements BaseAdapter interface for file-based credential retrieval.

Security:
- Enforces allowed/denied path patterns
- File size limits
- Permission checks
- No secrets in logs
"""

import os
import json
import yaml
import configparser
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from fnmatch import fnmatch

from .base_adapter import (
    BaseAdapter,
    ConnectionError,
    RetrievalError,
    EphemeralAccountError
)

logger = logging.getLogger(__name__)


class FilesAdapter(BaseAdapter):
    """
    Local file system adapter for credential retrieval
    
    Retrieves secrets from:
    - JSON files
    - YAML files
    - INI/conf files
    - Plain text files
    - Mounted network shares
    
    Security features:
    - Path whitelist/blacklist
    - File size limits
    - Permission validation
    - No directory traversal
    
    Example:
        adapter = FilesAdapter(config={
            "allowed_paths": ["/mnt/nas/*", "/opt/app/config/*"],
            "denied_paths": ["/etc/shadow", "*/private/*"],
            "max_file_size_mb": 10
        })
        
        adapter.connect(
            target={"base_path": "/mnt/nas"},
            credentials={}  # No credentials needed for local files
        )
        
        secret = adapter.retrieve(
            path="app/database.conf",
            parse_format="ini",
            extract_key="database.password"
        )
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize files adapter with security config"""
        super().__init__(config)
        
        # Security configuration
        self.allowed_paths = self.config.get("allowed_paths", [])
        self.denied_paths = self.config.get("denied_paths", [])
        self.max_file_size_mb = self.config.get("max_file_size_mb", 10)
        self.base_path = None
        
        logger.info(f"FilesAdapter initialized with {len(self.allowed_paths)} allowed patterns")
    
    def connect(self, target: Dict[str, Any], credentials: Dict[str, Any]) -> bool:
        """
        Connect to local file system
        
        Args:
            target: {"base_path": "/mnt/nas"} - Base directory path
            credentials: {} - Not used for local files
        
        Returns:
            True if base path exists and is accessible
        """
        try:
            base_path = target.get("base_path", "/")
            base_path = Path(base_path).resolve()
            
            # Verify base path exists
            if not base_path.exists():
                raise ConnectionError(f"Base path does not exist: {base_path}")
            
            # Verify base path is a directory
            if not base_path.is_dir():
                raise ConnectionError(f"Base path is not a directory: {base_path}")
            
            # Verify read permissions
            if not os.access(base_path, os.R_OK):
                raise ConnectionError(f"No read permission for base path: {base_path}")
            
            self.base_path = base_path
            self.connected = True
            
            self._log_operation("connect", {"base_path": str(base_path)})
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Failed to connect to file system: {e}")
    
    def retrieve(self, path: str, **options) -> bytes:
        """
        Retrieve file content
        
        Args:
            path: Relative path from base_path (e.g., "app/database.conf")
            **options:
                parse_format: "json", "yaml", "ini", "text" (default: auto-detect)
                extract_key: "database.password" (for structured files)
                encoding: "utf-8" (default), "latin-1", etc.
        
        Returns:
            File content as bytes (or extracted value if extract_key specified)
        
        Raises:
            RetrievalError: If retrieval fails
            FileNotFoundError: If file doesn't exist
            PermissionError: If access denied
        """
        if not self.connected:
            raise RetrievalError("Not connected - call connect() first")
        
        try:
            # Resolve full path
            full_path = (self.base_path / path).resolve()
            
            # Security checks
            self._validate_path(full_path)
            
            # Check file exists
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            
            # Check file size
            file_size_mb = full_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                raise RetrievalError(
                    f"File too large: {file_size_mb:.2f}MB (max: {self.max_file_size_mb}MB)"
                )
            
            # Read file
            encoding = options.get("encoding", "utf-8")
            with open(full_path, "rb") as f:
                content = f.read()
            
            # Parse if requested
            parse_format = options.get("parse_format")
            extract_key = options.get("extract_key")
            
            if extract_key:
                # Parse and extract specific key
                parsed = self._parse_content(content, parse_format, encoding, full_path)
                extracted = self._extract_key(parsed, extract_key)
                
                # Convert back to bytes
                if isinstance(extracted, str):
                    content = extracted.encode(encoding)
                elif isinstance(extracted, bytes):
                    content = extracted
                else:
                    content = str(extracted).encode(encoding)
            
            self._log_operation("retrieve", {
                "path": path,
                "size_bytes": len(content),
                "parse_format": parse_format,
                "extract_key": extract_key
            })
            
            return content
            
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"Retrieval failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            raise RetrievalError(f"Failed to retrieve file: {e}")
    
    def create_ephemeral_account(self, ttl_seconds: int, **options) -> Dict[str, Any]:
        """
        Not supported for file system adapter
        
        Raises:
            NotImplementedError: Files adapter doesn't support account creation
        """
        raise NotImplementedError(
            "FilesAdapter does not support ephemeral account creation"
        )
    
    def cleanup(self):
        """Cleanup - no resources to release for file system"""
        try:
            if self.connected:
                self._log_operation("cleanup", {})
                self.connected = False
                self.base_path = None
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def _validate_path(self, full_path: Path):
        """
        Validate path against security rules
        
        Args:
            full_path: Resolved absolute path
        
        Raises:
            PermissionError: If path violates security rules
        """
        path_str = str(full_path)
        
        # Check denied paths first (takes precedence)
        for denied_pattern in self.denied_paths:
            if fnmatch(path_str, denied_pattern):
                raise PermissionError(f"Access denied by policy: {denied_pattern}")
        
        # Check allowed paths (if configured)
        if self.allowed_paths:
            allowed = False
            for allowed_pattern in self.allowed_paths:
                if fnmatch(path_str, allowed_pattern):
                    allowed = True
                    break
            
            if not allowed:
                raise PermissionError(f"Path not in allowed list: {path_str}")
        
        # Check path is within base_path (prevent directory traversal)
        try:
            full_path.relative_to(self.base_path)
        except ValueError:
            raise PermissionError(f"Path outside base directory: {path_str}")
    
    def _parse_content(
        self,
        content: bytes,
        parse_format: Optional[str],
        encoding: str,
        file_path: Path
    ) -> Any:
        """
        Parse file content based on format
        
        Args:
            content: Raw file content
            parse_format: "json", "yaml", "ini", or None (auto-detect)
            encoding: Text encoding
            file_path: File path (for auto-detection)
        
        Returns:
            Parsed content (dict, list, or str)
        """
        # Auto-detect format if not specified
        if not parse_format:
            suffix = file_path.suffix.lower()
            if suffix in [".json"]:
                parse_format = "json"
            elif suffix in [".yaml", ".yml"]:
                parse_format = "yaml"
            elif suffix in [".ini", ".conf", ".cfg"]:
                parse_format = "ini"
            else:
                parse_format = "text"
        
        text = content.decode(encoding)
        
        if parse_format == "json":
            return json.loads(text)
        elif parse_format == "yaml":
            return yaml.safe_load(text)
        elif parse_format == "ini":
            parser = configparser.ConfigParser()
            parser.read_string(text)
            # Convert to dict
            return {section: dict(parser[section]) for section in parser.sections()}
        else:
            return text
    
    def _extract_key(self, data: Any, key_path: str) -> Any:
        """
        Extract value from nested structure using dot notation
        
        Args:
            data: Parsed data structure
            key_path: "database.password" or "config.db.host"
        
        Returns:
            Extracted value
        
        Raises:
            KeyError: If key not found
        """
        keys = key_path.split(".")
        current = data
        
        for key in keys:
            if isinstance(current, dict):
                current = current[key]
            else:
                raise KeyError(f"Cannot extract key '{key}' from non-dict: {type(current)}")
        
        return current

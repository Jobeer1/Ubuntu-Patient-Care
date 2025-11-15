"""
Unit tests for Files Adapter

Tests file-based credential retrieval with security validation.
"""

import pytest
import json
import yaml
import tempfile
from pathlib import Path

from adapters.files_adapter import FilesAdapter
from adapters.base_adapter import RetrievalError, ConnectionError


class TestFilesAdapter:
    """Test suite for FilesAdapter"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory with test files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create test files
            (tmpdir / "test.json").write_text(json.dumps({
                "database": {
                    "password": "secret123",
                    "host": "localhost"
                }
            }))
            
            (tmpdir / "test.yaml").write_text(yaml.dump({
                "config": {
                    "api_key": "key456",
                    "endpoint": "https://api.example.com"
                }
            }))
            
            (tmpdir / "test.ini").write_text("""
[database]
password = dbpass789
host = db.local
            """)
            
            (tmpdir / "test.txt").write_text("plain_secret")
            
            # Create subdirectory
            subdir = tmpdir / "subdir"
            subdir.mkdir()
            (subdir / "nested.json").write_text(json.dumps({"key": "value"}))
            
            yield tmpdir
    
    def test_connect_success(self, temp_dir):
        """Test successful connection to file system"""
        adapter = FilesAdapter()
        result = adapter.connect(
            target={"base_path": str(temp_dir)},
            credentials={}
        )
        
        assert result is True
        assert adapter.connected is True
        assert adapter.base_path == temp_dir
    
    def test_connect_nonexistent_path(self):
        """Test connection to nonexistent path fails"""
        adapter = FilesAdapter()
        
        with pytest.raises(ConnectionError, match="does not exist"):
            adapter.connect(
                target={"base_path": "/nonexistent/path"},
                credentials={}
            )
    
    def test_retrieve_json_file(self, temp_dir):
        """Test retrieving JSON file"""
        adapter = FilesAdapter()
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        content = adapter.retrieve("test.json")
        data = json.loads(content.decode("utf-8"))
        
        assert data["database"]["password"] == "secret123"
    
    def test_retrieve_with_extract_key(self, temp_dir):
        """Test extracting specific key from JSON"""
        adapter = FilesAdapter()
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        content = adapter.retrieve(
            "test.json",
            parse_format="json",
            extract_key="database.password"
        )
        
        assert content.decode("utf-8") == "secret123"
    
    def test_retrieve_yaml_file(self, temp_dir):
        """Test retrieving YAML file"""
        adapter = FilesAdapter()
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        content = adapter.retrieve(
            "test.yaml",
            parse_format="yaml",
            extract_key="config.api_key"
        )
        
        assert content.decode("utf-8") == "key456"
    
    def test_retrieve_ini_file(self, temp_dir):
        """Test retrieving INI file"""
        adapter = FilesAdapter()
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        content = adapter.retrieve(
            "test.ini",
            parse_format="ini",
            extract_key="database.password"
        )
        
        assert content.decode("utf-8").strip() == "dbpass789"
    
    def test_retrieve_plain_text(self, temp_dir):
        """Test retrieving plain text file"""
        adapter = FilesAdapter()
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        content = adapter.retrieve("test.txt")
        
        assert content.decode("utf-8") == "plain_secret"
    
    def test_retrieve_nested_file(self, temp_dir):
        """Test retrieving file from subdirectory"""
        adapter = FilesAdapter()
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        content = adapter.retrieve("subdir/nested.json")
        data = json.loads(content.decode("utf-8"))
        
        assert data["key"] == "value"
    
    def test_retrieve_nonexistent_file(self, temp_dir):
        """Test retrieving nonexistent file fails"""
        adapter = FilesAdapter()
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        with pytest.raises(FileNotFoundError):
            adapter.retrieve("nonexistent.txt")
    
    def test_retrieve_without_connect(self):
        """Test retrieving without connecting fails"""
        adapter = FilesAdapter()
        
        with pytest.raises(RetrievalError, match="Not connected"):
            adapter.retrieve("test.txt")
    
    def test_path_whitelist(self, temp_dir):
        """Test path whitelist enforcement"""
        adapter = FilesAdapter(config={
            "allowed_paths": [str(temp_dir / "test.json")]
        })
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        # Allowed file should work
        content = adapter.retrieve("test.json")
        assert content is not None
        
        # Non-allowed file should fail
        with pytest.raises(PermissionError, match="not in allowed list"):
            adapter.retrieve("test.txt")
    
    def test_path_blacklist(self, temp_dir):
        """Test path blacklist enforcement"""
        adapter = FilesAdapter(config={
            "denied_paths": [str(temp_dir / "test.txt")]
        })
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        # Non-denied file should work
        content = adapter.retrieve("test.json")
        assert content is not None
        
        # Denied file should fail
        with pytest.raises(PermissionError, match="Access denied"):
            adapter.retrieve("test.txt")
    
    def test_file_size_limit(self, temp_dir):
        """Test file size limit enforcement"""
        # Create large file
        large_file = temp_dir / "large.txt"
        large_file.write_text("x" * (11 * 1024 * 1024))  # 11MB
        
        adapter = FilesAdapter(config={"max_file_size_mb": 10})
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        with pytest.raises(RetrievalError, match="File too large"):
            adapter.retrieve("large.txt")
    
    def test_directory_traversal_prevention(self, temp_dir):
        """Test prevention of directory traversal attacks"""
        adapter = FilesAdapter()
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        # Try to access file outside base_path
        with pytest.raises(PermissionError, match="outside base directory"):
            adapter.retrieve("../../../etc/passwd")
    
    def test_cleanup(self, temp_dir):
        """Test cleanup releases resources"""
        adapter = FilesAdapter()
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        assert adapter.connected is True
        
        adapter.cleanup()
        
        assert adapter.connected is False
        assert adapter.base_path is None
    
    def test_context_manager(self, temp_dir):
        """Test adapter works as context manager"""
        with FilesAdapter() as adapter:
            adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
            content = adapter.retrieve("test.txt")
            assert content is not None
        
        # Should be cleaned up after context
        assert adapter.connected is False
    
    def test_ephemeral_account_not_supported(self, temp_dir):
        """Test ephemeral account creation raises NotImplementedError"""
        adapter = FilesAdapter()
        adapter.connect(target={"base_path": str(temp_dir)}, credentials={})
        
        with pytest.raises(NotImplementedError):
            adapter.create_ephemeral_account(ttl_seconds=3600)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

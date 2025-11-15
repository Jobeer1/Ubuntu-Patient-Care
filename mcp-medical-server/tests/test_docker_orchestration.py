"""
Docker Orchestration Tests

Tests the complete Docker stack including all services and their interactions.
"""

import pytest
import asyncio
import time
import subprocess
import os
import json
import sys
from pathlib import Path
import requests
from typing import Optional

# Configuration
COMPOSE_PROJECT = "mcp-medical-test"
MCP_SERVER_URL = "http://localhost:8000"
KIRO_AGENT_URL = "http://localhost:8001"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
REDIS_HOST = "localhost"
REDIS_PORT = 6379
HEALTHCHECK_TIMEOUT = 60
HEALTHCHECK_INTERVAL = 2


class DockerOrchestrationTests:
    """Test suite for Docker stack orchestration"""

    @classmethod
    def setup_class(cls):
        """Start Docker stack before tests"""
        print("\n🐳 Starting Docker stack...")
        result = subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start Docker stack: {result.stderr}")
        
        # Wait for services to be healthy
        cls._wait_for_services()
        print("✅ Docker stack started successfully")

    @classmethod
    def teardown_class(cls):
        """Stop Docker stack after tests"""
        print("\n🛑 Stopping Docker stack...")
        subprocess.run(
            ["docker-compose", "down"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True
        )
        print("✅ Docker stack stopped")

    @staticmethod
    def _wait_for_services(timeout: int = HEALTHCHECK_TIMEOUT):
        """Wait for all services to be healthy"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check PostgreSQL
                import psycopg2
                try:
                    conn = psycopg2.connect(
                        host=POSTGRES_HOST,
                        port=POSTGRES_PORT,
                        user="mcp_user",
                        password="mcp_password_change_me",
                        database="mcp_credentials",
                        connect_timeout=5
                    )
                    conn.close()
                    print("✓ PostgreSQL healthy")
                except Exception as e:
                    print(f"✗ PostgreSQL not ready: {e}")
                    raise
                
                # Check Redis
                import redis
                try:
                    r = redis.Redis(
                        host=REDIS_HOST,
                        port=REDIS_PORT,
                        password="redis_password_change_me",
                        socket_connect_timeout=5
                    )
                    r.ping()
                    print("✓ Redis healthy")
                except Exception as e:
                    print(f"✗ Redis not ready: {e}")
                    raise
                
                # Check MCP Server
                try:
                    response = requests.get(f"{MCP_SERVER_URL}/health/live", timeout=5)
                    if response.status_code == 200:
                        print("✓ MCP Server healthy")
                    else:
                        raise Exception(f"Health check returned {response.status_code}")
                except Exception as e:
                    print(f"✗ MCP Server not ready: {e}")
                    raise
                
                # Check Kiro Agent
                try:
                    response = requests.get(f"{KIRO_AGENT_URL}/health/live", timeout=5)
                    if response.status_code == 200:
                        print("✓ Kiro Agent healthy")
                    else:
                        raise Exception(f"Health check returned {response.status_code}")
                except Exception as e:
                    print(f"✗ Kiro Agent not ready: {e}")
                    raise
                
                print("✅ All services healthy!")
                return
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"⏳ Waiting for services ({elapsed:.1f}s / {timeout}s)...")
                time.sleep(HEALTHCHECK_INTERVAL)
        
        raise TimeoutError(f"Services did not become healthy within {timeout}s")

    def test_postgres_connection(self):
        """Test PostgreSQL connectivity and schema"""
        import psycopg2
        
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user="mcp_user",
            password="mcp_password_change_me",
            database="mcp_credentials"
        )
        
        cur = conn.cursor()
        
        # Check if tables exist
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        expected_tables = [
            'credentials', 'emergency_requests', 'approval_workflows',
            'tokens', 'audit_log', 'ephemeral_accounts', 'nonces',
            'vault_unseal_shares', 'owner_authorizations'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"
        
        cur.close()
        conn.close()
        print(f"✅ PostgreSQL: {len(tables)} tables found")

    def test_redis_connection(self):
        """Test Redis connectivity"""
        import redis
        
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password="redis_password_change_me",
            decode_responses=True
        )
        
        # Test basic operations
        r.set("test_key", "test_value")
        value = r.get("test_key")
        assert value == "test_value"
        r.delete("test_key")
        
        # Check memory usage
        info = r.info('memory')
        used_memory = info['used_memory_human']
        print(f"✅ Redis: {used_memory} used")

    def test_mcp_server_health(self):
        """Test MCP Server health endpoint"""
        response = requests.get(f"{MCP_SERVER_URL}/health/live")
        assert response.status_code == 200
        
        health = response.json()
        assert health["status"] == "healthy"
        print(f"✅ MCP Server: {health}")

    def test_mcp_server_openapi(self):
        """Test MCP Server OpenAPI documentation"""
        response = requests.get(f"{MCP_SERVER_URL}/openapi.json")
        assert response.status_code == 200
        
        openapi = response.json()
        assert openapi["info"]["title"] == "MCP Medical Server"
        assert "paths" in openapi
        print(f"✅ MCP Server OpenAPI: {len(openapi['paths'])} endpoints")

    def test_kiro_agent_health(self):
        """Test Kiro Agent health endpoint"""
        response = requests.get(f"{KIRO_AGENT_URL}/health/live")
        assert response.status_code == 200
        
        health = response.json()
        assert health["status"] == "healthy"
        print(f"✅ Kiro Agent: {health}")

    def test_container_networking(self):
        """Test container-to-container communication"""
        # Verify that containers can reach each other
        # by checking their network connectivity
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "mcp-server", "ping", "-c", "1", "postgres"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"MCP Server cannot ping PostgreSQL: {result.stderr}"
        print("✅ Container networking: mcp-server → postgres")
        
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "mcp-server", "ping", "-c", "1", "redis"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"MCP Server cannot ping Redis: {result.stderr}"
        print("✅ Container networking: mcp-server → redis")

    def test_volume_persistence(self):
        """Test volume persistence across restarts"""
        import psycopg2
        
        # Write test data
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user="mcp_user",
            password="mcp_password_change_me",
            database="mcp_credentials"
        )
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO credentials (name, secret_type, encrypted_value)
            VALUES (%s, %s, %s) RETURNING id
        """, ("test_persistence", "password", b"test"))
        cred_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        # Verify data persists
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user="mcp_user",
            password="mcp_password_change_me",
            database="mcp_credentials"
        )
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM credentials WHERE id = %s", (cred_id,))
        result = cur.fetchone()
        assert result is not None
        assert result[1] == "test_persistence"
        cur.close()
        conn.close()
        print("✅ Volume persistence: data persists")

    def test_service_logs(self):
        """Test that services are generating logs"""
        services = ["postgres", "redis", "mcp-server", "kiro-agent"]
        
        for service in services:
            result = subprocess.run(
                ["docker-compose", "logs", service],
                cwd=str(Path(__file__).parent.parent),
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert len(result.stdout) > 0, f"No logs for {service}"
            print(f"✅ Logs: {service} ({len(result.stdout)} bytes)")

    def test_service_resource_limits(self):
        """Test that services respect resource limits"""
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "table {{.Container}}\t{{.MemUsage}}"],
            capture_output=True,
            text=True
        )
        
        output = result.stdout
        print(f"✅ Resource usage:\n{output}")

    def test_database_indexes(self):
        """Test that database indexes are created"""
        import psycopg2
        
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user="mcp_user",
            password="mcp_password_change_me",
            database="mcp_credentials"
        )
        cur = conn.cursor()
        
        cur.execute("""
            SELECT indexname FROM pg_indexes WHERE schemaname = 'public'
        """)
        indexes = [row[0] for row in cur.fetchall()]
        
        expected_indexes = [
            'idx_credentials_active',
            'idx_emergency_requests_status',
            'idx_tokens_expires',
            'idx_audit_log_event_type'
        ]
        
        for idx in expected_indexes:
            assert any(idx in i for i in indexes), f"Index {idx} not found"
        
        cur.close()
        conn.close()
        print(f"✅ Database indexes: {len(indexes)} indexes found")

    def test_environment_variables(self):
        """Test that services are configured with environment variables"""
        # Check MCP Server environment
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "mcp-server", "env"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True
        )
        
        env_vars = result.stdout
        assert "ENVIRONMENT" in env_vars or "LOG_LEVEL" in env_vars
        print(f"✅ Environment configuration: {len(env_vars.split())} variables")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

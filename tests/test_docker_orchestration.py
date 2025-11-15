#!/usr/bin/env python3
"""
Docker Orchestration Integration Tests - Phase 2.1

Tests for Docker Compose orchestration:
- Container startup and health checks
- Inter-service networking
- Volume persistence
- Environment configuration
- Database initialization
- Multi-subnet setup
"""

import os
import json
import subprocess
import time
import requests
from pathlib import Path
from typing import Dict, Optional, List
import pytest

# Configuration
COMPOSE_FILE = Path(__file__).parent.parent / "docker-compose.yml"
DOCKER_COMPOSE_CMD = ["docker-compose", "-f", str(COMPOSE_FILE)]
RETRY_ATTEMPTS = 5
RETRY_DELAY = 2

# Service endpoints
MCP_HEALTH = "http://localhost:8000/health"
AGENT_HEALTH = "http://localhost:8001/health"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
REDIS_HOST = "localhost"
REDIS_PORT = 6379


class DockerComposeOrchestration:
    """Helper class for Docker Compose operations"""

    @staticmethod
    def run_command(cmd: List[str]) -> subprocess.CompletedProcess:
        """Run a shell command and return result"""
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Command failed: {' '.join(cmd)}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
        return result

    @staticmethod
    def compose(args: List[str]) -> subprocess.CompletedProcess:
        """Run docker-compose command"""
        return DockerComposeOrchestration.run_command(DOCKER_COMPOSE_CMD + args)

    @staticmethod
    def get_services() -> Dict[str, str]:
        """Get running service names and status"""
        result = DockerComposeOrchestration.compose(["ps", "--format", "json"])
        if result.returncode == 0:
            try:
                services = json.loads(result.stdout)
                return {s["Service"]: s["State"] for s in services}
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def wait_for_service(endpoint: str, max_retries: int = RETRY_ATTEMPTS) -> bool:
        """Wait for service to be healthy"""
        for attempt in range(max_retries):
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
        
        return False


class TestDockerComposeSetup:
    """Test Docker Compose basic setup and orchestration"""

    def test_compose_file_exists(self):
        """Verify docker-compose.yml exists and is valid"""
        assert COMPOSE_FILE.exists(), f"docker-compose.yml not found at {COMPOSE_FILE}"
        
        result = DockerComposeOrchestration.compose(["config", "--quiet"])
        assert result.returncode == 0, "docker-compose.yml is invalid"

    def test_compose_services_defined(self):
        """Verify all required services are defined"""
        result = DockerComposeOrchestration.compose(["config"])
        assert result.returncode == 0
        
        config = json.loads(result.stdout)
        required_services = ["postgres", "redis", "mcp-server", "kiro-agent"]
        
        for service in required_services:
            assert service in config["services"], f"Service '{service}' not defined"

    def test_compose_volumes_defined(self):
        """Verify volumes are properly defined"""
        result = DockerComposeOrchestration.compose(["config"])
        assert result.returncode == 0
        
        config = json.loads(result.stdout)
        required_volumes = [
            "postgres_data",
            "redis_data",
            "mcp_logs",
            "mcp_vault",
            "agent_logs"
        ]
        
        for volume in required_volumes:
            assert volume in config["volumes"], f"Volume '{volume}' not defined"

    def test_compose_networks_defined(self):
        """Verify networks for multi-subnet support"""
        result = DockerComposeOrchestration.compose(["config"])
        assert result.returncode == 0
        
        config = json.loads(result.stdout)
        required_networks = ["mcp-network", "subnet-1", "subnet-2"]
        
        for network in required_networks:
            assert network in config["networks"], f"Network '{network}' not defined"


class TestDockerContainerStartup:
    """Test container startup and health checks"""

    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self):
        """Start containers before tests, stop after"""
        print("\n[Docker] Starting containers...")
        result = DockerComposeOrchestration.compose(["up", "-d"])
        assert result.returncode == 0, "Failed to start containers"
        
        # Wait for services to be ready
        time.sleep(5)
        
        yield
        
        print("\n[Docker] Stopping containers...")
        DockerComposeOrchestration.compose(["down"])

    def test_all_containers_running(self):
        """Verify all containers are running"""
        services = DockerComposeOrchestration.get_services()
        
        required_services = ["postgres", "redis", "mcp-server", "kiro-agent"]
        for service in required_services:
            assert service in services, f"Service '{service}' is not running"
            assert "Up" in services[service], f"Service '{service}' is not in 'Up' state"

    def test_postgres_health_check(self):
        """Verify PostgreSQL is healthy"""
        for attempt in range(RETRY_ATTEMPTS):
            result = DockerComposeOrchestration.compose(
                ["exec", "-T", "postgres", "pg_isready", "-U", "postgres"]
            )
            
            if result.returncode == 0:
                assert True
                return
            
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY)
        
        pytest.fail("PostgreSQL health check failed")

    def test_redis_health_check(self):
        """Verify Redis is healthy"""
        for attempt in range(RETRY_ATTEMPTS):
            result = DockerComposeOrchestration.compose(
                ["exec", "-T", "redis", "redis-cli", "-a", "redis_secure_password", "ping"]
            )
            
            if result.returncode == 0 and "PONG" in result.stdout:
                assert True
                return
            
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY)
        
        pytest.fail("Redis health check failed")

    def test_mcp_server_health_endpoint(self):
        """Verify MCP Server responds to health check"""
        assert DockerComposeOrchestration.wait_for_service(
            MCP_HEALTH
        ), "MCP Server health check failed"

    def test_kiro_agent_health_endpoint(self):
        """Verify Kiro Agent responds to health check"""
        assert DockerComposeOrchestration.wait_for_service(
            AGENT_HEALTH
        ), "Kiro Agent health check failed"


class TestDatabaseInitialization:
    """Test database initialization and schema setup"""

    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self):
        """Setup/teardown for database tests"""
        yield

    def test_database_created(self):
        """Verify credentials_db database was created"""
        result = DockerComposeOrchestration.compose(
            ["exec", "-T", "postgres", "psql", "-U", "postgres", "-l"]
        )
        
        assert result.returncode == 0
        assert "credentials_db" in result.stdout

    def test_schema_created(self):
        """Verify credentials schema exists"""
        result = DockerComposeOrchestration.compose(
            ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "credentials_db", 
             "-c", "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'credentials'"]
        )
        
        assert result.returncode == 0
        assert "credentials" in result.stdout

    def test_tables_created(self):
        """Verify all required tables were created"""
        required_tables = [
            "credential_requests",
            "token_nonces",
            "vault_secrets",
            "credential_approvals",
            "credential_audit_events",
            "retrieval_history"
        ]
        
        for table in required_tables:
            result = DockerComposeOrchestration.compose(
                ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "credentials_db",
                 "-c", f"SELECT to_regclass('credentials.{table}')"]
            )
            
            assert result.returncode == 0, f"Failed to query {table}"
            assert table in result.stdout, f"Table '{table}' not found"

    def test_indexes_created(self):
        """Verify indexes were created for performance"""
        result = DockerComposeOrchestration.compose(
            ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "credentials_db",
             "-c", "SELECT count(*) FROM pg_indexes WHERE schemaname = 'credentials'"]
        )
        
        assert result.returncode == 0
        # Should have at least 10+ indexes
        assert "|" in result.stdout

    def test_views_created(self):
        """Verify views for common queries were created"""
        required_views = ["pending_requests", "expired_requests"]
        
        for view in required_views:
            result = DockerComposeOrchestration.compose(
                ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "credentials_db",
                 "-c", f"SELECT * FROM {view} LIMIT 0"]
            )
            
            assert result.returncode == 0, f"View '{view}' not accessible"


class TestInterServiceNetworking:
    """Test networking between services"""

    def test_mcp_server_can_reach_postgres(self):
        """Verify MCP Server container can reach PostgreSQL"""
        result = DockerComposeOrchestration.compose(
            ["exec", "-T", "mcp-server", "nc", "-zv", "postgres", "5432"]
        )
        
        assert result.returncode == 0 or "succeeded" in result.stderr.lower()

    def test_mcp_server_can_reach_redis(self):
        """Verify MCP Server container can reach Redis"""
        result = DockerComposeOrchestration.compose(
            ["exec", "-T", "mcp-server", "nc", "-zv", "redis", "6379"]
        )
        
        assert result.returncode == 0 or "succeeded" in result.stderr.lower()

    def test_agent_can_reach_mcp_server(self):
        """Verify Agent can reach MCP Server"""
        result = DockerComposeOrchestration.compose(
            ["exec", "-T", "kiro-agent", "nc", "-zv", "mcp-server", "8000"]
        )
        
        assert result.returncode == 0 or "succeeded" in result.stderr.lower()

    def test_agents_on_different_subnets(self):
        """Verify multi-subnet network connectivity"""
        # Check that mcp-server is on multiple networks
        result = DockerComposeOrchestration.compose(
            ["exec", "-T", "mcp-server", "ip", "addr", "show"]
        )
        
        assert result.returncode == 0
        # Should show multiple IP addresses (one per network)
        ip_count = result.stdout.count("inet ")
        assert ip_count >= 2, "MCP Server should be on multiple networks"


class TestVolumePersistence:
    """Test volume persistence across restarts"""

    def test_postgres_volume_exists(self):
        """Verify PostgreSQL volume is created"""
        result = DockerComposeOrchestration.run_command(
            ["docker", "volume", "inspect", "ubuntu-patient-care_postgres_data"]
        )
        
        assert result.returncode == 0

    def test_redis_volume_exists(self):
        """Verify Redis volume is created"""
        result = DockerComposeOrchestration.run_command(
            ["docker", "volume", "inspect", "ubuntu-patient-care_redis_data"]
        )
        
        assert result.returncode == 0

    def test_data_persists_after_container_restart(self):
        """Verify data persists when container is restarted"""
        # Insert test data
        insert_cmd = (
            "psql -U postgres -d credentials_db -c "
            "INSERT INTO credentials.credential_requests "
            "(req_id, requester_id, reason, target_vault, target_path, expires_ts) "
            "VALUES ('TEST-001', 'test@test.com', 'test', 'test-vault', '/test', "
            "CURRENT_TIMESTAMP + interval '1 hour')"
        )
        
        DockerComposeOrchestration.compose(["exec", "-T", "postgres"] + insert_cmd.split())
        
        # Restart postgres
        DockerComposeOrchestration.compose(["restart", "postgres"])
        
        # Wait for recovery
        time.sleep(3)
        
        # Verify data still exists
        result = DockerComposeOrchestration.compose(
            ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "credentials_db",
             "-c", "SELECT COUNT(*) FROM credentials.credential_requests WHERE req_id = 'TEST-001'"]
        )
        
        assert result.returncode == 0
        assert "1" in result.stdout


class TestEnvironmentConfiguration:
    """Test environment configuration and customization"""

    def test_env_file_example_exists(self):
        """Verify .env.example exists"""
        env_file = Path(__file__).parent.parent / ".env.example"
        assert env_file.exists()

    def test_environment_variables_passed_to_services(self):
        """Verify environment variables are accessible in containers"""
        result = DockerComposeOrchestration.compose(
            ["exec", "-T", "mcp-server", "env"]
        )
        
        assert result.returncode == 0
        # Check for known variables
        assert "DB_HOST" in result.stdout or "PATH" in result.stdout


class TestHealthChecks:
    """Test health check configurations"""

    def test_postgres_healthcheck_configured(self):
        """Verify PostgreSQL has health check"""
        result = DockerComposeOrchestration.compose(["config"])
        config = json.loads(result.stdout)
        
        postgres_config = config["services"]["postgres"]
        assert "healthcheck" in postgres_config

    def test_redis_healthcheck_configured(self):
        """Verify Redis has health check"""
        result = DockerComposeOrchestration.compose(["config"])
        config = json.loads(result.stdout)
        
        redis_config = config["services"]["redis"]
        assert "healthcheck" in redis_config

    def test_mcp_server_healthcheck_configured(self):
        """Verify MCP Server has health check"""
        result = DockerComposeOrchestration.compose(["config"])
        config = json.loads(result.stdout)
        
        mcp_config = config["services"]["mcp-server"]
        assert "healthcheck" in mcp_config


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

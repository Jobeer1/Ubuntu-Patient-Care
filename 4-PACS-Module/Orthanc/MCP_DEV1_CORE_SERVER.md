# Developer 1: Core MCP Server & Infrastructure

**Role:** Backend Infrastructure Lead  
**Primary Focus:** FastAPI server, tool registry, API gateway, deployment, DevOps  
**Estimated Effort:** 12 weeks (full-time)

---

## Phase 1: Foundation (Weeks 1-4)

### Week 1: Project Setup & Core Server

#### Task 1.1: Repository & Environment Setup
**Estimated Time:** 4 hours  
**Priority:** Critical

- [ ] Create Git repository structure:
  ```
  ubuntu-patient-care-mcp/
  ├── server/
  ├── adapters/
  ├── llm/
  ├── security/
  ├── tests/
  ├── deployment/
  └── docs/
  ```
- [ ] Initialize Python project:
  - [ ] Create `requirements.txt` with core dependencies:
    ```
    fastapi==0.104.1
    uvicorn[standard]==0.24.0
    pydantic==2.5.0
    python-jose[cryptography]==3.3.0
    httpx==0.25.0
    pytest==7.4.3
    pytest-asyncio==0.21.1
    ```
  - [ ] Setup `.gitignore` for Python projects
  - [ ] Create `.env.example` for configuration templates
- [ ] Setup pre-commit hooks (black, flake8, mypy)
- [ ] Create initial `README.md` with setup instructions

**Deliverables:** Repository structure, environment setup guide

---

#### Task 1.2: FastAPI Server Skeleton
**Estimated Time:** 8 hours  
**Priority:** Critical  
**Dependencies:** Task 1.1

- [ ] Create `server/main.py` with FastAPI app initialization:
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  
  app = FastAPI(
      title="Ubuntu Patient Care MCP Server",
      version="0.1.0",
      description="Model Context Protocol server for healthcare modules"
  )
  
  # Add CORS middleware
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],  # Configure properly in production
      allow_methods=["*"],
      allow_headers=["*"]
  )
  
  @app.get("/health")
  async def health_check():
      return {"status": "healthy", "version": "0.1.0"}
  ```

- [ ] Create `server/config.py` for configuration management:
  ```python
  from pydantic_settings import BaseSettings
  
  class Settings(BaseSettings):
      orthanc_url: str = "http://localhost:8042"
      ris_db_url: str = "postgresql://user:pass@localhost/ris"
      reporting_api_url: str = "http://localhost:5000"
      billing_api_url: str = "http://localhost:3000"
      jwt_secret_key: str
      
      class Config:
          env_file = ".env"
  ```

- [ ] Setup logging infrastructure:
  - [ ] Create `server/logging_config.py` with structured logging (JSON format)
  - [ ] Add request ID tracking middleware
  - [ ] Configure log levels (DEBUG for dev, INFO for prod)

- [ ] Test server startup:
  ```bash
  uvicorn server.main:app --reload --port 8000
  ```

**Deliverables:** Working FastAPI server responding to `/health` endpoint

---

#### Task 1.3: Tool Registry System
**Estimated Time:** 12 hours  
**Priority:** Critical  
**Dependencies:** Task 1.2

- [ ] Create `server/tool_registry.py`:
  ```python
  from typing import Dict, List, Callable, Any
  from pydantic import BaseModel
  
  class ToolDefinition(BaseModel):
      name: str
      description: str
      parameters: Dict[str, Any]  # JSON Schema
      returns: Dict[str, Any]
      examples: List[Dict[str, Any]] = []
  
  class ToolRegistry:
      def __init__(self):
          self._tools: Dict[str, ToolDefinition] = {}
          self._handlers: Dict[str, Callable] = {}
      
      def register_tool(self, tool: ToolDefinition, handler: Callable):
          """Register a tool with its handler function"""
          self._tools[tool.name] = tool
          self._handlers[tool.name] = handler
      
      def get_tool(self, name: str) -> ToolDefinition:
          """Retrieve tool definition"""
          return self._tools.get(name)
      
      def list_tools(self) -> List[ToolDefinition]:
          """List all registered tools"""
          return list(self._tools.values())
      
      async def invoke_tool(self, name: str, parameters: Dict) -> Any:
          """Execute a tool with given parameters"""
          if name not in self._handlers:
              raise ValueError(f"Tool {name} not found")
          
          handler = self._handlers[name]
          return await handler(**parameters)
  
  # Global registry instance
  registry = ToolRegistry()
  ```

- [ ] Create API endpoints in `server/routes/tools.py`:
  ```python
  from fastapi import APIRouter, HTTPException
  from server.tool_registry import registry
  
  router = APIRouter(prefix="/mcp/v1", tags=["tools"])
  
  @router.get("/tools")
  async def list_tools():
      """List all available tools"""
      return {"tools": [tool.dict() for tool in registry.list_tools()]}
  
  @router.post("/invoke")
  async def invoke_tool(request: ToolInvocationRequest):
      """Invoke a specific tool"""
      try:
          result = await registry.invoke_tool(
              request.tool,
              request.parameters
          )
          return {"success": True, "result": result}
      except Exception as e:
          raise HTTPException(status_code=400, detail=str(e))
  ```

- [ ] Add router to main app in `server/main.py`
- [ ] Write unit tests for tool registry:
  - [ ] Test tool registration
  - [ ] Test tool listing
  - [ ] Test tool invocation
  - [ ] Test error handling for missing tools

**Deliverables:** Tool registry system with API endpoints, 100% unit test coverage

---

### Week 2: Authentication & Request Handling

#### Task 1.4: Authentication Middleware
**Estimated Time:** 10 hours  
**Priority:** High  
**Collaboration:** Work with Dev 4 on security requirements

- [ ] Create `server/auth_middleware.py`:
  ```python
  from fastapi import Request, HTTPException
  from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
  from jose import jwt, JWTError
  
  security = HTTPBearer()
  
  async def verify_token(
      credentials: HTTPAuthorizationCredentials = Depends(security)
  ) -> Dict:
      """Verify JWT token and return user claims"""
      try:
          payload = jwt.decode(
              credentials.credentials,
              settings.jwt_secret_key,
              algorithms=["HS256"]
          )
          return payload
      except JWTError:
          raise HTTPException(status_code=401, detail="Invalid token")
  ```

- [ ] Add authentication to protected routes:
  ```python
  @router.post("/invoke")
  async def invoke_tool(
      request: ToolInvocationRequest,
      user: Dict = Depends(verify_token)
  ):
      # Store user context for audit logging
      request.state.user = user
      # ... rest of invocation logic
  ```

- [ ] Create token generation endpoint for testing:
  ```python
  @router.post("/auth/token")
  async def create_token(credentials: UserCredentials):
      # Validate credentials (mock for now)
      token = jwt.encode(
          {"user_id": credentials.username, "role": "radiologist"},
          settings.jwt_secret_key,
          algorithm="HS256"
      )
      return {"access_token": token, "token_type": "bearer"}
  ```

- [ ] Write tests for authentication:
  - [ ] Valid token acceptance
  - [ ] Invalid token rejection
  - [ ] Expired token handling
  - [ ] Missing token handling

**Deliverables:** Working JWT authentication system

---

#### Task 1.5: Request Validation & Error Handling
**Estimated Time:** 8 hours  
**Priority:** Medium  
**Dependencies:** Task 1.3

- [ ] Create Pydantic models for all request types in `server/models/`:
  ```python
  # server/models/requests.py
  from pydantic import BaseModel, Field
  from typing import Dict, Any, Optional
  
  class ToolInvocationRequest(BaseModel):
      tool: str = Field(..., description="Tool name to invoke")
      parameters: Dict[str, Any] = Field(default_factory=dict)
      context: Optional[Dict[str, str]] = None
  
  class ChatRequest(BaseModel):
      message: str = Field(..., min_length=1, max_length=5000)
      user_id: str
      session_id: Optional[str] = None
  ```

- [ ] Create standardized error responses in `server/errors.py`:
  ```python
  from fastapi import HTTPException
  
  class MCPError(HTTPException):
      def __init__(self, status_code: int, error_code: str, message: str):
          super().__init__(
              status_code=status_code,
              detail={
                  "error_code": error_code,
                  "message": message,
                  "timestamp": datetime.utcnow().isoformat()
              }
          )
  
  class ToolNotFoundError(MCPError):
      def __init__(self, tool_name: str):
          super().__init__(404, "TOOL_NOT_FOUND", f"Tool '{tool_name}' not found")
  ```

- [ ] Add global exception handler in `main.py`:
  ```python
  @app.exception_handler(Exception)
  async def global_exception_handler(request: Request, exc: Exception):
      # Log error with request context
      logger.error(f"Unhandled exception: {exc}", exc_info=True)
      return JSONResponse(
          status_code=500,
          content={"error": "Internal server error", "request_id": request.state.request_id}
      )
  ```

- [ ] Write tests for validation and error handling

**Deliverables:** Robust request validation and standardized error responses

---

### Week 3: Integration Support & Docker Setup

#### Task 1.6: Adapter Interface Definition
**Estimated Time:** 6 hours  
**Priority:** Critical  
**Collaboration:** Coordinate with Dev 2 & Dev 3

- [ ] Create `adapters/base_adapter.py`:
  ```python
  from abc import ABC, abstractmethod
  from typing import Dict, Any
  
  class ModuleAdapter(ABC):
      """Base class for all module adapters"""
      
      def __init__(self, config: Dict[str, Any]):
          self.config = config
      
      @abstractmethod
      async def initialize(self) -> None:
          """Initialize connection to target module"""
          pass
      
      @abstractmethod
      async def health_check(self) -> bool:
          """Verify module connectivity and health"""
          pass
      
      @abstractmethod
      async def invoke_tool(self, tool_name: str, params: Dict) -> Dict:
          """Execute a tool and return structured result"""
          pass
      
      async def shutdown(self) -> None:
          """Cleanup resources"""
          pass
  ```

- [ ] Document adapter contract in `docs/ADAPTER_INTERFACE.md`:
  - [ ] Method signatures and requirements
  - [ ] Error handling expectations
  - [ ] Example implementation
  - [ ] Testing requirements

- [ ] Create adapter integration helpers in `server/adapter_manager.py`:
  ```python
  class AdapterManager:
      def __init__(self):
          self.adapters: Dict[str, ModuleAdapter] = {}
      
      async def register_adapter(self, name: str, adapter: ModuleAdapter):
          await adapter.initialize()
          self.adapters[name] = adapter
      
      async def health_check_all(self) -> Dict[str, bool]:
          results = {}
          for name, adapter in self.adapters.items():
              results[name] = await adapter.health_check()
          return results
  ```

- [ ] Share interface spec with Dev 2 and Dev 3

**Deliverables:** Adapter interface specification, integration helpers

---

#### Task 1.7: Docker & Docker Compose Setup
**Estimated Time:** 10 hours  
**Priority:** High  
**Dependencies:** Task 1.2

- [ ] Create `Dockerfile`:
  ```dockerfile
  FROM python:3.11-slim
  
  WORKDIR /app
  
  # Install system dependencies
  RUN apt-get update && apt-get install -y \
      build-essential \
      && rm -rf /var/lib/apt/lists/*
  
  # Copy requirements and install Python deps
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  
  # Copy application code
  COPY server/ ./server/
  COPY adapters/ ./adapters/
  COPY security/ ./security/
  
  # Expose port
  EXPOSE 8000
  
  # Health check
  HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"
  
  # Run server
  CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

- [ ] Create `docker-compose.dev.yml`:
  ```yaml
  version: '3.8'
  
  services:
    mcp-server:
      build: .
      ports:
        - "8000:8000"
      volumes:
        - ./server:/app/server
        - ./adapters:/app/adapters
      environment:
        - ORTHANC_URL=http://orthanc:8042
        - RIS_DB_URL=postgresql://ris:ris@ris-db:5432/ris
        - REPORTING_API_URL=http://reporting:5000
        - BILLING_API_URL=http://billing:3000
        - JWT_SECRET_KEY=dev-secret-key-change-in-prod
      depends_on:
        - orthanc
        - ris-db
      networks:
        - mcp-network
    
    orthanc:
      image: jodogne/orthanc-plugins:latest
      ports:
        - "8042:8042"
      environment:
        - ORTHANC_USERNAME=orthanc
        - ORTHANC_PASSWORD=orthanc
      volumes:
        - orthanc-data:/var/lib/orthanc/db
      networks:
        - mcp-network
    
    ris-db:
      image: postgres:15
      environment:
        - POSTGRES_DB=ris
        - POSTGRES_USER=ris
        - POSTGRES_PASSWORD=ris
      volumes:
        - ris-data:/var/lib/postgresql/data
      ports:
        - "5432:5432"
      networks:
        - mcp-network
  
  volumes:
    orthanc-data:
    ris-data:
  
  networks:
    mcp-network:
      driver: bridge
  ```

- [ ] Create startup script `scripts/dev-start.sh`:
  ```bash
  #!/bin/bash
  echo "Starting development environment..."
  docker-compose -f docker-compose.dev.yml up -d
  echo "Waiting for services to be ready..."
  sleep 10
  docker-compose -f docker-compose.dev.yml logs -f mcp-server
  ```

- [ ] Test Docker setup:
  ```bash
  docker-compose -f docker-compose.dev.yml build
  docker-compose -f docker-compose.dev.yml up -d
  curl http://localhost:8000/health
  ```

- [ ] Document Docker setup in `docs/DOCKER_SETUP.md`

**Deliverables:** Working Docker development environment

---

### Week 4: Testing & Documentation

#### Task 1.8: Integration Testing Framework
**Estimated Time:** 12 hours  
**Priority:** High

- [ ] Setup pytest fixtures in `tests/conftest.py`:
  ```python
  import pytest
  from httpx import AsyncClient
  from server.main import app
  
  @pytest.fixture
  async def client():
      async with AsyncClient(app=app, base_url="http://test") as ac:
          yield ac
  
  @pytest.fixture
  def auth_headers():
      # Generate test JWT token
      token = create_test_token(user_id="test_user", role="admin")
      return {"Authorization": f"Bearer {token}"}
  ```

- [ ] Create integration tests in `tests/integration/`:
  - [ ] `test_api_health.py`: Health check endpoint
  - [ ] `test_tool_registry.py`: Tool registration and listing
  - [ ] `test_tool_invocation.py`: Tool invocation flow
  - [ ] `test_authentication.py`: Auth middleware
  - [ ] `test_error_handling.py`: Error responses

- [ ] Setup test coverage reporting:
  ```bash
  pytest --cov=server --cov-report=html --cov-report=term
  ```

- [ ] Achieve 80%+ code coverage for core server

**Deliverables:** Integration test suite, coverage report

---

#### Task 1.9: API Documentation
**Estimated Time:** 6 hours  
**Priority:** Medium

- [ ] Configure Swagger/OpenAPI in `main.py`:
  ```python
  app = FastAPI(
      title="Ubuntu Patient Care MCP Server",
      description="""
      Model Context Protocol server providing unified access to:
      - PACS (Orthanc DICOM server)
      - RIS (Radiology Information System)
      - Medical Reporting Module
      - Billing/Accounting Module
      """,
      version="0.1.0",
      docs_url="/docs",
      redoc_url="/redoc"
  )
  ```

- [ ] Add comprehensive docstrings to all endpoints:
  ```python
  @router.post("/invoke", response_model=ToolInvocationResponse)
  async def invoke_tool(request: ToolInvocationRequest):
      """
      Invoke a specific MCP tool.
      
      Args:
          request: Tool invocation request with tool name and parameters
      
      Returns:
          Tool execution result with success status and data
      
      Raises:
          HTTPException: 400 if tool not found or invalid parameters
          HTTPException: 401 if authentication fails
          HTTPException: 500 if tool execution fails
      
      Example:
          ```json
          {
            "tool": "pacs_search_studies",
            "parameters": {"patient_id": "P12345", "modality": "CT"}
          }
          ```
      """
  ```

- [ ] Generate OpenAPI spec:
  ```bash
  python -c "from server.main import app; import json; print(json.dumps(app.openapi()))" > docs/openapi.json
  ```

- [ ] Create `docs/API.md` with usage examples

**Deliverables:** Comprehensive API documentation (Swagger + Markdown)

---

## Phase 2: Multi-Module Integration (Weeks 5-8)

### Week 5-6: Performance Optimization & Monitoring

#### Task 1.10: Request Metrics & Logging
**Estimated Time:** 8 hours  
**Priority:** High

- [ ] Add Prometheus metrics in `server/metrics.py`:
  ```python
  from prometheus_client import Counter, Histogram, Gauge
  
  request_count = Counter('mcp_requests_total', 'Total requests', ['method', 'endpoint'])
  request_duration = Histogram('mcp_request_duration_seconds', 'Request duration')
  active_requests = Gauge('mcp_active_requests', 'Active requests')
  tool_invocations = Counter('mcp_tool_invocations_total', 'Tool invocations', ['tool_name', 'status'])
  ```

- [ ] Add metrics middleware:
  ```python
  @app.middleware("http")
  async def metrics_middleware(request: Request, call_next):
      active_requests.inc()
      start_time = time.time()
      
      response = await call_next(request)
      
      duration = time.time() - start_time
      request_count.labels(method=request.method, endpoint=request.url.path).inc()
      request_duration.observe(duration)
      active_requests.dec()
      
      return response
  ```

- [ ] Create `/metrics` endpoint:
  ```python
  from prometheus_client import generate_latest
  
  @app.get("/metrics")
  async def metrics():
      return Response(content=generate_latest(), media_type="text/plain")
  ```

- [ ] Setup Grafana dashboard JSON in `deployment/grafana/mcp-dashboard.json`

**Deliverables:** Prometheus metrics, Grafana dashboard template

---

#### Task 1.11: Connection Pooling & Caching
**Estimated Time:** 10 hours  
**Priority:** Medium

- [ ] Implement HTTP client pooling for adapters:
  ```python
  # server/http_client.py
  import httpx
  
  class HTTPClientPool:
      def __init__(self, max_connections: int = 100):
          self.client = httpx.AsyncClient(
              limits=httpx.Limits(
                  max_connections=max_connections,
                  max_keepalive_connections=20
              ),
              timeout=httpx.Timeout(10.0)
          )
      
      async def close(self):
          await self.client.aclose()
  
  # Global client pool
  http_pool = HTTPClientPool()
  ```

- [ ] Add Redis caching layer (optional):
  ```python
  from redis import asyncio as aioredis
  
  class CacheManager:
      def __init__(self, redis_url: str):
          self.redis = aioredis.from_url(redis_url)
      
      async def get(self, key: str):
          value = await self.redis.get(key)
          return json.loads(value) if value else None
      
      async def set(self, key: str, value: Any, expire: int = 300):
          await self.redis.setex(key, expire, json.dumps(value))
  ```

- [ ] Add caching to frequently accessed tools (e.g., patient lookups)

**Deliverables:** Optimized connection handling, optional caching layer

---

### Week 7-8: Load Testing & Stability

#### Task 1.12: Load Testing
**Estimated Time:** 10 hours  
**Priority:** High

- [ ] Create Locust load test scripts in `tests/load/`:
  ```python
  # tests/load/locustfile.py
  from locust import HttpUser, task, between
  
  class MCPUser(HttpUser):
      wait_time = between(1, 3)
      
      def on_start(self):
          # Authenticate
          response = self.client.post("/auth/token", json={
              "username": "test_user",
              "password": "test_pass"
          })
          self.token = response.json()["access_token"]
      
      @task(3)
      def list_tools(self):
          self.client.get("/mcp/v1/tools", headers={
              "Authorization": f"Bearer {self.token}"
          })
      
      @task(7)
      def invoke_pacs_search(self):
          self.client.post("/mcp/v1/invoke", json={
              "tool": "pacs_search_studies",
              "parameters": {"patient_id": f"P{random.randint(1, 100):05d}"}
          }, headers={"Authorization": f"Bearer {self.token}"})
  ```

- [ ] Run load tests:
  ```bash
  locust -f tests/load/locustfile.py --host=http://localhost:8000
  ```

- [ ] Document performance benchmarks in `docs/PERFORMANCE.md`:
  - [ ] Requests per second capacity
  - [ ] 95th/99th percentile latencies
  - [ ] Memory usage under load
  - [ ] Recommended scaling thresholds

**Deliverables:** Load testing suite, performance benchmark report

---

#### Task 1.13: Error Recovery & Circuit Breakers
**Estimated Time:** 12 hours  
**Priority:** High

- [ ] Implement circuit breaker for adapter calls:
  ```python
  # server/circuit_breaker.py
  from enum import Enum
  import time
  
  class CircuitState(Enum):
      CLOSED = "closed"  # Normal operation
      OPEN = "open"      # Failing, reject requests
      HALF_OPEN = "half_open"  # Testing recovery
  
  class CircuitBreaker:
      def __init__(self, failure_threshold: int = 5, timeout: int = 60):
          self.failure_threshold = failure_threshold
          self.timeout = timeout
          self.failure_count = 0
          self.last_failure_time = None
          self.state = CircuitState.CLOSED
      
      async def call(self, func, *args, **kwargs):
          if self.state == CircuitState.OPEN:
              if time.time() - self.last_failure_time > self.timeout:
                  self.state = CircuitState.HALF_OPEN
              else:
                  raise Exception("Circuit breaker is OPEN")
          
          try:
              result = await func(*args, **kwargs)
              self.on_success()
              return result
          except Exception as e:
              self.on_failure()
              raise e
      
      def on_success(self):
          self.failure_count = 0
          self.state = CircuitState.CLOSED
      
      def on_failure(self):
          self.failure_count += 1
          self.last_failure_time = time.time()
          if self.failure_count >= self.failure_threshold:
              self.state = CircuitState.OPEN
  ```

- [ ] Add retry logic with exponential backoff:
  ```python
  from tenacity import retry, stop_after_attempt, wait_exponential
  
  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
  async def call_adapter_with_retry(adapter, tool_name, params):
      return await adapter.invoke_tool(tool_name, params)
  ```

- [ ] Test failure scenarios:
  - [ ] Adapter service down
  - [ ] Network timeout
  - [ ] Database connection failure

**Deliverables:** Resilient error handling, circuit breaker implementation

---

## Phase 3: Production Readiness (Weeks 9-12)

### Week 9-10: Kubernetes Deployment

#### Task 1.14: Kubernetes Manifests
**Estimated Time:** 16 hours  
**Priority:** Critical

- [ ] Create `deployment/kubernetes/namespace.yaml`:
  ```yaml
  apiVersion: v1
  kind: Namespace
  metadata:
    name: mcp-server
  ```

- [ ] Create `deployment/kubernetes/configmap.yaml`:
  ```yaml
  apiVersion: v1
  kind: ConfigMap
  metadata:
    name: mcp-config
    namespace: mcp-server
  data:
    ORTHANC_URL: "http://orthanc-service:8042"
    RIS_DB_URL: "postgresql://ris:ris@postgres-service:5432/ris"
    # ... other config
  ```

- [ ] Create `deployment/kubernetes/secret.yaml`:
  ```yaml
  apiVersion: v1
  kind: Secret
  metadata:
    name: mcp-secrets
    namespace: mcp-server
  type: Opaque
  data:
    jwt-secret: <base64-encoded-secret>
    db-password: <base64-encoded-password>
  ```

- [ ] Create `deployment/kubernetes/deployment.yaml`:
  ```yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: mcp-server
    namespace: mcp-server
  spec:
    replicas: 3
    selector:
      matchLabels:
        app: mcp-server
    template:
      metadata:
        labels:
          app: mcp-server
      spec:
        containers:
        - name: mcp-server
          image: your-registry/mcp-server:latest
          ports:
          - containerPort: 8000
          env:
          - name: JWT_SECRET_KEY
            valueFrom:
              secretKeyRef:
                name: mcp-secrets
                key: jwt-secret
          envFrom:
          - configMapRef:
              name: mcp-config
          resources:
            requests:
              cpu: "2000m"
              memory: "4Gi"
            limits:
              cpu: "4000m"
              memory: "8Gi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
  ```

- [ ] Create `deployment/kubernetes/service.yaml`:
  ```yaml
  apiVersion: v1
  kind: Service
  metadata:
    name: mcp-server-service
    namespace: mcp-server
  spec:
    type: LoadBalancer
    selector:
      app: mcp-server
    ports:
    - port: 80
      targetPort: 8000
      protocol: TCP
  ```

- [ ] Create `deployment/kubernetes/hpa.yaml` (Horizontal Pod Autoscaler):
  ```yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: mcp-server-hpa
    namespace: mcp-server
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: mcp-server
    minReplicas: 3
    maxReplicas: 10
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  ```

- [ ] Create deployment script `deployment/deploy.sh`:
  ```bash
  #!/bin/bash
  kubectl apply -f kubernetes/namespace.yaml
  kubectl apply -f kubernetes/configmap.yaml
  kubectl apply -f kubernetes/secret.yaml
  kubectl apply -f kubernetes/deployment.yaml
  kubectl apply -f kubernetes/service.yaml
  kubectl apply -f kubernetes/hpa.yaml
  
  echo "Waiting for deployment..."
  kubectl rollout status deployment/mcp-server -n mcp-server
  ```

- [ ] Test deployment on staging cluster
- [ ] Document deployment process in `docs/KUBERNETES_DEPLOYMENT.md`

**Deliverables:** Production-ready Kubernetes manifests, deployment scripts

---

### Week 11: Monitoring & Observability

#### Task 1.15: Production Monitoring Setup
**Estimated Time:** 10 hours  
**Priority:** High

- [ ] Deploy Prometheus to K8s cluster:
  ```bash
  kubectl create namespace monitoring
  helm install prometheus prometheus-community/prometheus -n monitoring
  ```

- [ ] Create ServiceMonitor for MCP server:
  ```yaml
  apiVersion: monitoring.coreos.com/v1
  kind: ServiceMonitor
  metadata:
    name: mcp-server-monitor
    namespace: mcp-server
  spec:
    selector:
      matchLabels:
        app: mcp-server
    endpoints:
    - port: metrics
      path: /metrics
      interval: 30s
  ```

- [ ] Deploy Grafana:
  ```bash
  helm install grafana grafana/grafana -n monitoring
  ```

- [ ] Import dashboards:
  - [ ] Request rate and latency
  - [ ] Error rates by tool
  - [ ] Resource utilization (CPU/memory)
  - [ ] Active connections

- [ ] Setup alerting rules in `deployment/prometheus/alerts.yaml`:
  ```yaml
  groups:
  - name: mcp-alerts
    rules:
    - alert: HighErrorRate
      expr: rate(mcp_requests_total{status="error"}[5m]) > 0.05
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High error rate detected"
    
    - alert: HighLatency
      expr: histogram_quantile(0.99, mcp_request_duration_seconds_bucket) > 5
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "99th percentile latency > 5s"
  ```

**Deliverables:** Production monitoring with Prometheus and Grafana

---

### Week 12: Final Polish & Handoff

#### Task 1.16: CI/CD Pipeline
**Estimated Time:** 8 hours  
**Priority:** Medium

- [ ] Create `.github/workflows/ci.yml` (or GitLab CI equivalent):
  ```yaml
  name: CI Pipeline
  
  on:
    push:
      branches: [main, develop]
    pull_request:
      branches: [main]
  
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=server --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
    
    build:
      needs: test
      runs-on: ubuntu-latest
      steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t mcp-server:${{ github.sha }} .
      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker push mcp-server:${{ github.sha }}
  ```

- [ ] Create deployment workflow for production

**Deliverables:** Automated CI/CD pipeline

---

#### Task 1.17: Documentation Finalization
**Estimated Time:** 6 hours  
**Priority:** High

- [ ] Complete `README.md` with:
  - [ ] Project overview
  - [ ] Architecture diagram
  - [ ] Quick start guide
  - [ ] Deployment instructions
  - [ ] Contributing guidelines

- [ ] Create runbook `docs/RUNBOOK.md`:
  - [ ] Common troubleshooting steps
  - [ ] Scaling procedures
  - [ ] Backup and recovery
  - [ ] Incident response procedures

- [ ] Record demo video showing:
  - [ ] Local development setup
  - [ ] Tool invocation examples
  - [ ] Monitoring dashboards

**Deliverables:** Complete documentation package

---

## Success Metrics

### Code Quality
- ✅ 80%+ test coverage for core server
- ✅ All tests passing in CI
- ✅ Zero high/critical security vulnerabilities (Snyk scan)
- ✅ Code follows PEP 8 style guide

### Performance
- ✅ Health check responds in < 50ms
- ✅ Tool listing responds in < 100ms
- ✅ Tool invocation overhead < 50ms (excluding adapter time)
- ✅ Server handles 100 concurrent requests without degradation

### Deployment
- ✅ Docker Compose dev environment working
- ✅ Kubernetes production deployment functional
- ✅ Auto-scaling working correctly
- ✅ Monitoring dashboards displaying real-time metrics

---

## Collaboration Points

### With Dev 2 (PACS/RIS):
- **Week 2**: Share adapter interface spec
- **Week 3**: Integrate PACS adapter into tool registry
- **Week 5**: Integrate RIS adapter
- **Week 8**: Joint integration testing

### With Dev 3 (Reporting/Billing):
- **Week 2**: Share adapter interface spec
- **Week 4**: Integrate reporting adapter
- **Week 6**: Integrate billing adapter

### With Dev 4 (LLM/Security):
- **Week 2**: Collaborate on authentication design
- **Week 4**: Integrate LLM agent with tool registry
- **Week 9**: Security audit and hardening
- **Week 11**: Setup audit logging monitoring

---

## Tools & Technologies

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Testing:** pytest, pytest-asyncio, Locust
- **Containerization:** Docker, Docker Compose
- **Orchestration:** Kubernetes, Helm
- **Monitoring:** Prometheus, Grafana
- **CI/CD:** GitHub Actions (or GitLab CI)
- **Security:** python-jose (JWT), Bandit (security linting)

---

**Good luck, Developer 1! You're building the backbone of the MCP system. 🚀**

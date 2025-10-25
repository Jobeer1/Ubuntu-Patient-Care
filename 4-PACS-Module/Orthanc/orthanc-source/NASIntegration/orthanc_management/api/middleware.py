"""
Orthanc Management API - Middleware Components
Security, audit, and rate limiting middleware
"""

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging
import json
import hashlib
from typing import Dict, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security headers and basic protection middleware"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Add security headers
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Remove server information
        response.headers.pop("Server", None)
        
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    """Audit logging middleware for compliance tracking"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.excluded_paths = {
            "/health",
            "/health/detailed",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/favicon.ico"
        }
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Skip audit for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Capture request details
        request_data = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": self._generate_request_id(request)
        }
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Capture response details
            response_data = {
                "status_code": response.status_code,
                "process_time": round(process_time, 4),
                "success": 200 <= response.status_code < 400
            }
            
            # Log audit entry
            await self._log_audit_entry(request_data, response_data)
            
            # Add response headers
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_data["request_id"]
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            response_data = {
                "status_code": 500,
                "process_time": round(process_time, 4),
                "success": False,
                "error": str(e)
            }
            
            await self._log_audit_entry(request_data, response_data)
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _generate_request_id(self, request: Request) -> str:
        """Generate unique request ID"""
        timestamp = str(time.time())
        client_ip = self._get_client_ip(request)
        path = request.url.path
        
        hash_input = f"{timestamp}-{client_ip}-{path}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
    
    async def _log_audit_entry(self, request_data: Dict[str, Any], response_data: Dict[str, Any]):
        """Log audit entry for compliance"""
        try:
            # Combine request and response data
            audit_entry = {
                **request_data,
                **response_data,
                "audit_type": "api_access",
                "compliance_category": "api_audit"
            }
            
            # Log to application logger
            if response_data["success"]:
                logger.info(f"API Access: {request_data['method']} {request_data['path']} - {response_data['status_code']} ({response_data['process_time']}s)")
            else:
                logger.warning(f"API Error: {request_data['method']} {request_data['path']} - {response_data['status_code']} ({response_data['process_time']}s)")
            
            # TODO: Store in audit database table when available
            # await audit_manager.create_log(...audit_entry)
            
        except Exception as e:
            logger.error(f"Failed to log audit entry: {str(e)}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent abuse"""
    
    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: Dict[str, deque] = defaultdict(deque)
        self.excluded_paths = {
            "/health",
            "/health/detailed",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json"
        }
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old requests (older than 1 minute)
        minute_ago = current_time - 60
        while (self.request_counts[client_ip] and 
               self.request_counts[client_ip][0] < minute_ago):
            self.request_counts[client_ip].popleft()
        
        # Check rate limit
        if len(self.request_counts[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": 429,
                        "message": "Rate limit exceeded",
                        "details": f"Maximum {self.requests_per_minute} requests per minute allowed",
                        "retry_after": 60
                    }
                },
                headers={"Retry-After": "60"}
            )
        
        # Add current request
        self.request_counts[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.requests_per_minute - len(self.request_counts[client_ip]))
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Optional authentication middleware for protected routes"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.public_paths = {
            "/",
            "/health",
            "/health/detailed",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/reset-password"
        }
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public paths
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        # Check for authentication header
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": 401,
                        "message": "Authentication required",
                        "details": "Bearer token required for this endpoint"
                    }
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Extract token
        token = authorization.split(" ")[1]
        
        # TODO: Validate token with AuthManager
        # For now, just pass through
        
        return await call_next(request)


class CacheMiddleware(BaseHTTPMiddleware):
    """Simple caching middleware for GET requests"""
    
    def __init__(self, app: ASGIApp, cache_ttl: int = 300):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cacheable_paths = {
            "/api/dashboard/stats",
            "/api/doctors",
            "/api/configurations"
        }
    
    async def dispatch(self, request: Request, call_next):
        # Only cache GET requests for specific paths
        if (request.method != "GET" or 
            request.url.path not in self.cacheable_paths):
            return await call_next(request)
        
        # Create cache key
        cache_key = f"{request.url.path}?{request.url.query}"
        current_time = time.time()
        
        # Check cache
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if current_time - cache_entry["timestamp"] < self.cache_ttl:
                logger.debug(f"Cache hit for: {cache_key}")
                response = Response(
                    content=cache_entry["content"],
                    status_code=cache_entry["status_code"],
                    headers=cache_entry["headers"]
                )
                response.headers["X-Cache"] = "HIT"
                return response
        
        # Process request
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200:
            # Read response content
            content = b""
            async for chunk in response.body_iterator:
                content += chunk
            
            # Store in cache
            self.cache[cache_key] = {
                "content": content,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "timestamp": current_time
            }
            
            # Create new response
            response = Response(
                content=content,
                status_code=response.status_code,
                headers=response.headers
            )
            response.headers["X-Cache"] = "MISS"
        
        return response

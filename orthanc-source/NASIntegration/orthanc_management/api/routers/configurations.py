"""
Orthanc Management API - Configuration Router
CRUD operations for Orthanc configurations with template support
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from orthanc_management.api.auth import User
from orthanc_management.api.routers.auth import get_current_active_user, get_auth_manager
from orthanc_management.managers.config_manager import ConfigManager
from orthanc_management.models.orthanc_config import OrthancConfig
from orthanc_management.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

# Pydantic models for request/response
class ConfigCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    config_type: str = Field(..., max_length=50)
    template_name: Optional[str] = Field(None, max_length=100)
    config_data: Dict[str, Any] = Field(...)
    environment: str = Field(default="development", max_length=20)
    version: str = Field(default="1.0.0", max_length=20)
    is_active: bool = Field(default=True)
    tags: Optional[List[str]] = Field(default=[])

class ConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    config_type: Optional[str] = Field(None, max_length=50)
    template_name: Optional[str] = Field(None, max_length=100)
    config_data: Optional[Dict[str, Any]] = None
    environment: Optional[str] = Field(None, max_length=20)
    version: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None

class ConfigResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    config_type: str
    template_name: Optional[str]
    config_data: Dict[str, Any]
    environment: str
    version: str
    is_active: bool
    tags: List[str]
    created_by: Optional[str]
    created_at: str
    updated_at: str

class ConfigListResponse(BaseModel):
    configurations: List[ConfigResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class ConfigStatsResponse(BaseModel):
    total_configurations: int
    active_configurations: int
    inactive_configurations: int
    by_type: Dict[str, int]
    by_environment: Dict[str, int]
    by_template: Dict[str, int]
    recent_changes: List[Dict[str, Any]]

class ConfigTemplate(BaseModel):
    name: str
    description: str
    config_type: str
    template_data: Dict[str, Any]
    variables: List[str]
    example_values: Dict[str, Any]

class ConfigValidation(BaseModel):
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]

# Router instance
router = APIRouter(prefix="/configurations", tags=["Configurations"])

# Dependency to get database session
def get_db():
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

# Dependency to get config manager
def get_config_manager(db = Depends(get_db)):
    return ConfigManager(db)


@router.post("/", response_model=ConfigResponse)
async def create_configuration(
    config_data: ConfigCreate,
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Create a new Orthanc configuration
    Requires 'write' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "write")
        
        # Add created_by information
        config_dict = config_data.dict()
        config_dict["created_by"] = current_user.id
        
        # Create configuration
        config = config_manager.create_config(config_dict)
        
        logger.info(f"Configuration created by {current_user.username}: {config.name}")
        
        return ConfigResponse(**config.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create configuration"
        )


@router.get("/", response_model=ConfigListResponse)
async def list_configurations(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    config_type: Optional[str] = Query(None, description="Filter by configuration type"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    template_name: Optional[str] = Query(None, description="Filter by template name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    List configurations with pagination and filtering
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Build filters
        filters = {}
        if config_type:
            filters["config_type"] = config_type
        if environment:
            filters["environment"] = environment
        if template_name:
            filters["template_name"] = template_name
        if is_active is not None:
            filters["is_active"] = is_active
        if search:
            filters["search"] = search
        
        # Get configurations
        result = config_manager.get_configs_paginated(
            page=page,
            per_page=per_page,
            filters=filters
        )
        
        return ConfigListResponse(
            configurations=[ConfigResponse(**config.to_dict()) for config in result["configurations"]],
            total=result["total"],
            page=page,
            per_page=per_page,
            total_pages=result["total_pages"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list configurations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configurations"
        )


@router.get("/stats", response_model=ConfigStatsResponse)
async def get_configuration_stats(
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Get configuration statistics and analytics
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Get statistics
        stats = config_manager.get_config_statistics()
        
        return ConfigStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get configuration stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration statistics"
        )


@router.get("/templates", response_model=List[ConfigTemplate])
async def get_configuration_templates(
    config_type: Optional[str] = Query(None, description="Filter by configuration type"),
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Get available configuration templates
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Get templates
        templates = config_manager.get_available_templates(config_type)
        
        return [ConfigTemplate(**template) for template in templates]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get configuration templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration templates"
        )


@router.get("/{config_id}", response_model=ConfigResponse)
async def get_configuration(
    config_id: str,
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Get configuration by ID
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Get configuration
        config = config_manager.get_config(config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        
        return ConfigResponse(**config.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration"
        )


@router.put("/{config_id}", response_model=ConfigResponse)
async def update_configuration(
    config_id: str,
    config_data: ConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Update configuration by ID
    Requires 'write' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "write")
        
        # Filter out None values
        update_data = {k: v for k, v in config_data.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )
        
        # Update configuration
        config = config_manager.update_config(config_id, update_data)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        
        logger.info(f"Configuration updated by {current_user.username}: {config.name}")
        
        return ConfigResponse(**config.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )


@router.delete("/{config_id}")
async def delete_configuration(
    config_id: str,
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Delete configuration by ID
    Requires 'delete' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "delete")
        
        # Delete configuration
        success = config_manager.delete_config(config_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        
        logger.info(f"Configuration deleted by {current_user.username}: {config_id}")
        
        return {"message": "Configuration deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration"
        )


@router.post("/{config_id}/validate", response_model=ConfigValidation)
async def validate_configuration(
    config_id: str,
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Validate configuration syntax and structure
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Get configuration
        config = config_manager.get_config(config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        
        # Validate configuration
        validation_result = config_manager.validate_config(config.config_data, config.config_type)
        
        return ConfigValidation(**validation_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate configuration"
        )


@router.post("/{config_id}/deploy")
async def deploy_configuration(
    config_id: str,
    target_environment: str = Query(..., description="Target environment for deployment"),
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Deploy configuration to target environment
    Requires 'admin' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "admin")
        
        # Deploy configuration
        deployment_result = config_manager.deploy_config(config_id, target_environment)
        
        logger.info(f"Configuration deployed by {current_user.username}: {config_id} to {target_environment}")
        
        return {
            "message": "Configuration deployed successfully",
            "config_id": config_id,
            "target_environment": target_environment,
            "deployment_id": deployment_result.get("deployment_id"),
            "deployed_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deploy configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deploy configuration"
        )


@router.post("/{config_id}/clone")
async def clone_configuration(
    config_id: str,
    new_name: str = Query(..., description="Name for the cloned configuration"),
    new_environment: Optional[str] = Query(None, description="Environment for the cloned configuration"),
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Clone existing configuration
    Requires 'write' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "write")
        
        # Clone configuration
        cloned_config = config_manager.clone_config(
            config_id=config_id,
            new_name=new_name,
            new_environment=new_environment,
            created_by=current_user.id
        )
        
        logger.info(f"Configuration cloned by {current_user.username}: {config_id} -> {new_name}")
        
        return ConfigResponse(**cloned_config.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clone configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clone configuration"
        )


@router.get("/{config_id}/export")
async def export_configuration(
    config_id: str,
    format: str = Query("json", regex="^(json|yaml|xml)$", description="Export format"),
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Export configuration in specified format
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Export configuration
        export_data = config_manager.export_config(config_id, format)
        
        logger.info(f"Configuration exported by {current_user.username}: {config_id} as {format}")
        
        # Determine content type
        content_types = {
            "json": "application/json",
            "yaml": "application/x-yaml",
            "xml": "application/xml"
        }
        
        from fastapi.responses import Response
        return Response(
            content=export_data,
            media_type=content_types[format],
            headers={
                "Content-Disposition": f"attachment; filename=config_{config_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export configuration"
        )


@router.post("/import")
async def import_configuration(
    config_file: str = Query(..., description="Configuration file content"),
    format: str = Query("json", regex="^(json|yaml|xml)$", description="Import format"),
    environment: str = Query("development", description="Target environment"),
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Import configuration from file content
    Requires 'write' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "write")
        
        # Import configuration
        imported_config = config_manager.import_config(
            config_content=config_file,
            format=format,
            environment=environment,
            created_by=current_user.id
        )
        
        logger.info(f"Configuration imported by {current_user.username}: {imported_config.name}")
        
        return ConfigResponse(**imported_config.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import configuration"
        )


@router.get("/backup/all")
async def backup_all_configurations(
    environment: Optional[str] = Query(None, description="Filter by environment"),
    current_user: User = Depends(get_current_active_user),
    config_manager: ConfigManager = Depends(get_config_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Create backup of all configurations
    Requires 'admin' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "admin")
        
        # Create backup
        backup_data = config_manager.backup_all_configs(environment)
        
        logger.info(f"Configuration backup created by {current_user.username}")
        
        from fastapi.responses import Response
        return Response(
            content=backup_data,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=orthanc_configs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to backup configurations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to backup configurations"
        )

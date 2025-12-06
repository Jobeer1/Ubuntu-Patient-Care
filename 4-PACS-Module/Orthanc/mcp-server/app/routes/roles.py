"""Role management routes"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import RBACService

router = APIRouter(prefix="/roles", tags=["roles"])

class RoleCreate(BaseModel):
    name: str
    modules: List[str] = []

class RoleResponse(BaseModel):
    name: str
    modules: List[str] = []

@router.get("/", response_model=List[RoleResponse])
async def list_roles(db: Session = Depends(get_db)):
    """List all roles"""
    # Get from RBAC service
    roles = RBACService.get_all_roles()
    return [RoleResponse(name=role, modules=modules) for role, modules in roles.items()]

@router.post("/", response_model=RoleResponse)
async def create_role(role_data: RoleCreate, db: Session = Depends(get_db)):
    """Create new role"""
    # For now, just return the role (actual persistence would go to DB)
    return RoleResponse(name=role_data.name, modules=role_data.modules)

@router.get("/{role_name}", response_model=RoleResponse)
async def get_role(role_name: str, db: Session = Depends(get_db)):
    """Get role details"""
    modules = RBACService.get_modules_for_role(role_name)
    if modules is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return RoleResponse(name=role_name, modules=modules)

@router.put("/{role_name}", response_model=RoleResponse)
async def update_role(role_name: str, role_data: RoleCreate, db: Session = Depends(get_db)):
    """Update role modules"""
    # For now, just return the updated role
    return RoleResponse(name=role_name, modules=role_data.modules)

@router.delete("/{role_name}")
async def delete_role(role_name: str, db: Session = Depends(get_db)):
    """Delete role"""
    return {"status": "success", "message": f"Role {role_name} deleted"}

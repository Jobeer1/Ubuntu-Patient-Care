"""
Core adapter registry and transformation functions.

This module provides the plugin system for FHIR adapters.
"""

from typing import Dict, Any, Type, Optional
from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """Base class for all FHIR adapters"""
    
    resource_type: str = None
    
    @abstractmethod
    def to_fhir(self, local_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert local database record to FHIR resource.
        
        Args:
            local_record: Dictionary with local database fields
            
        Returns:
            Valid FHIR resource as dictionary
        """
        pass
    
    @abstractmethod
    def from_fhir(self, fhir_resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert FHIR resource to local database format.
        
        Args:
            fhir_resource: FHIR resource dictionary
            
        Returns:
            Local database record dictionary
        """
        pass
    
    @classmethod
    def register(cls):
        """Register this adapter in the global registry"""
        if cls.resource_type is None:
            raise ValueError(f"{cls.__name__} must define resource_type")
        _ADAPTER_REGISTRY[cls.resource_type] = cls()


# Global adapter registry
_ADAPTER_REGISTRY: Dict[str, BaseAdapter] = {}


def register_adapter(resource_type: str, adapter: BaseAdapter):
    """
    Register a custom adapter.
    
    Args:
        resource_type: FHIR resource type (e.g., 'Patient')
        adapter: Instance of BaseAdapter
    """
    _ADAPTER_REGISTRY[resource_type] = adapter


def to_fhir(resource_type: str, local_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert local record to FHIR resource.
    
    Args:
        resource_type: FHIR resource type (e.g., 'Patient')
        local_record: Local database record
        
    Returns:
        FHIR resource dictionary
        
    Raises:
        ValueError: If no adapter registered for resource_type
    """
    adapter = _ADAPTER_REGISTRY.get(resource_type)
    if adapter is None:
        raise ValueError(f"No adapter registered for resource type: {resource_type}")
    
    return adapter.to_fhir(local_record)


def from_fhir(resource_type: str, fhir_resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert FHIR resource to local format.
    
    Args:
        resource_type: FHIR resource type
        fhir_resource: FHIR resource dictionary
        
    Returns:
        Local database record dictionary
        
    Raises:
        ValueError: If no adapter registered for resource_type
    """
    adapter = _ADAPTER_REGISTRY.get(resource_type)
    if adapter is None:
        raise ValueError(f"No adapter registered for resource type: {resource_type}")
    
    return adapter.from_fhir(fhir_resource)


def get_registered_adapters() -> list[str]:
    """Get list of registered resource types"""
    return list(_ADAPTER_REGISTRY.keys())

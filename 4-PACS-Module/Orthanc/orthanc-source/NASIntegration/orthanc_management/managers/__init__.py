"""
Orthanc Management Managers Package
Business logic layer for the Orthanc Management Module
"""

from .doctor_manager import DoctorManager
from .authorization_manager import AuthorizationManager
from .config_manager import ConfigManager
from .audit_manager import AuditManager

__all__ = [
    'DoctorManager',
    'AuthorizationManager', 
    'ConfigManager',
    'AuditManager',
    'ManagerFactory'
]


class ManagerFactory:
    """
    Factory class for creating and managing business logic managers
    Provides a centralized way to access all managers with a shared database connection
    """
    
    def __init__(self, db_manager):
        """
        Initialize the manager factory
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
        self._doctor_manager = None
        self._authorization_manager = None
        self._config_manager = None
        self._audit_manager = None
    
    @property
    def doctor_manager(self) -> DoctorManager:
        """Get or create doctor manager"""
        if self._doctor_manager is None:
            self._doctor_manager = DoctorManager(self.db_manager)
        return self._doctor_manager
    
    @property
    def authorization_manager(self) -> AuthorizationManager:
        """Get or create authorization manager"""
        if self._authorization_manager is None:
            self._authorization_manager = AuthorizationManager(self.db_manager)
        return self._authorization_manager
    
    @property
    def config_manager(self) -> ConfigManager:
        """Get or create configuration manager"""
        if self._config_manager is None:
            self._config_manager = ConfigManager(self.db_manager)
        return self._config_manager
    
    @property
    def audit_manager(self) -> AuditManager:
        """Get or create audit manager"""
        if self._audit_manager is None:
            self._audit_manager = AuditManager(self.db_manager)
        return self._audit_manager
    
    def get_all_managers(self) -> dict:
        """Get all managers as a dictionary"""
        return {
            'doctor': self.doctor_manager,
            'authorization': self.authorization_manager,
            'config': self.config_manager,
            'audit': self.audit_manager
        }
    
    def test_all_connections(self) -> dict:
        """Test all manager database connections"""
        results = {}
        managers = self.get_all_managers()
        
        for name, manager in managers.items():
            try:
                # Test the database connection
                health = self.db_manager.get_health_status()
                results[name] = {
                    'status': 'healthy' if health['healthy'] else 'unhealthy',
                    'database_type': health.get('database_type'),
                    'connection_pool_size': health.get('connection_pool_size')
                }
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results

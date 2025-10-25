"""
Orthanc Management Business Logic - Configuration Manager
Handles Orthanc server configuration management
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
import json

from ..database.manager import DatabaseManager
from ..models.orthanc_config import OrthancConfig
from ..models.audit_log import AuditLog


class ConfigManager:
    """
    Business logic manager for Orthanc configuration
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_config(self, config_name: str, config_data: Dict[str, Any],
                     description: str = None, environment: str = 'production',
                     is_active: bool = False, created_by: str = None) -> Tuple[OrthancConfig, list]:
        """
        Create a new configuration
        
        Returns:
            Tuple of (config, validation_errors)
        """
        try:
            with self.db_manager.get_session() as session:
                # Create config instance
                config = OrthancConfig(
                    config_name=config_name,
                    description=description,
                    environment=environment,
                    is_active=is_active
                )
                
                # Set configuration data
                config.set_config_data(config_data)
                
                # Validate
                errors = config.validate()
                if errors:
                    return None, errors
                
                # Check for duplicate name in same environment
                existing = self.get_config_by_name(config_name, environment, session)
                if existing:
                    return None, [f"Configuration '{config_name}' already exists in {environment} environment"]
                
                # If setting as active, deactivate others in same environment
                if is_active:
                    self._deactivate_other_configs(environment, session)
                
                # Save
                session.add(config)
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='create_config',
                    resource_id=config.id,
                    user_id=created_by,
                    details={
                        'config_name': config_name,
                        'environment': environment,
                        'is_active': is_active,
                        'config_keys': list(config_data.keys())
                    },
                    session=session
                )
                
                return config, []
                
        except Exception as e:
            return None, [f"Database error: {str(e)}"]
    
    def get_config_by_id(self, config_id: str, session: Session = None) -> Optional[OrthancConfig]:
        """Get configuration by ID"""
        def _get_config(s):
            return s.query(OrthancConfig).filter(OrthancConfig.id == config_id).first()
        
        if session:
            return _get_config(session)
        else:
            with self.db_manager.get_session() as s:
                return _get_config(s)
    
    def get_config_by_name(self, config_name: str, environment: str = 'production',
                          session: Session = None) -> Optional[OrthancConfig]:
        """Get configuration by name and environment"""
        def _get_config(s):
            return s.query(OrthancConfig).filter(
                and_(
                    OrthancConfig.config_name == config_name,
                    OrthancConfig.environment == environment
                )
            ).first()
        
        if session:
            return _get_config(session)
        else:
            with self.db_manager.get_session() as s:
                return _get_config(s)
    
    def get_active_config(self, environment: str = 'production') -> Optional[OrthancConfig]:
        """Get the active configuration for an environment"""
        try:
            with self.db_manager.get_session() as session:
                return session.query(OrthancConfig).filter(
                    and_(
                        OrthancConfig.environment == environment,
                        OrthancConfig.is_active == True
                    )
                ).first()
        except Exception:
            return None
    
    def list_configs(self, environment: str = None, active_only: bool = False,
                    limit: int = 100, offset: int = 0) -> List[OrthancConfig]:
        """List configurations with filters"""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(OrthancConfig)
                
                if environment:
                    query = query.filter(OrthancConfig.environment == environment)
                
                if active_only:
                    query = query.filter(OrthancConfig.is_active == True)
                
                query = query.order_by(desc(OrthancConfig.created_at))
                
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)
                
                return query.all()
                
        except Exception:
            return []
    
    def update_config(self, config_id: str, updates: Dict[str, Any],
                     updated_by: str = None) -> Tuple[OrthancConfig, list]:
        """Update configuration"""
        try:
            with self.db_manager.get_session() as session:
                config = self.get_config_by_id(config_id, session)
                if not config:
                    return None, ["Configuration not found"]
                
                # Store original values for audit
                original_values = {}
                
                # Handle config_data separately
                if 'config_data' in updates:
                    original_values['config_data'] = config.get_config_data()
                    config.set_config_data(updates['config_data'])
                    del updates['config_data']
                
                # Apply other updates
                for field, value in updates.items():
                    if hasattr(config, field):
                        original_values[field] = getattr(config, field)
                        setattr(config, field, value)
                
                # Validate
                errors = config.validate()
                if errors:
                    return None, errors
                
                # Check for duplicate name if name changed
                if 'config_name' in updates:
                    existing = self.get_config_by_name(
                        updates['config_name'], config.environment, session
                    )
                    if existing and existing.id != config_id:
                        return None, [f"Configuration name '{updates['config_name']}' already exists"]
                
                # If setting as active, deactivate others
                if updates.get('is_active') == True and not config.is_active:
                    self._deactivate_other_configs(config.environment, session, exclude_id=config_id)
                
                # Update version and timestamp
                config.version += 1
                config.last_updated = datetime.utcnow()
                
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='update_config',
                    resource_id=config.id,
                    user_id=updated_by,
                    details={
                        'config_name': config.config_name,
                        'environment': config.environment,
                        'version': config.version,
                        'updates': {k: v for k, v in updates.items() if k != 'config_data'},
                        'config_data_changed': 'config_data' in original_values
                    },
                    session=session
                )
                
                return config, []
                
        except Exception as e:
            return None, [f"Database error: {str(e)}"]
    
    def activate_config(self, config_id: str, activated_by: str = None) -> Tuple[bool, list]:
        """Activate a configuration (deactivating others in same environment)"""
        try:
            with self.db_manager.get_session() as session:
                config = self.get_config_by_id(config_id, session)
                if not config:
                    return False, ["Configuration not found"]
                
                if config.is_active:
                    return False, ["Configuration is already active"]
                
                # Deactivate other configs in same environment
                self._deactivate_other_configs(config.environment, session)
                
                # Activate this config
                config.is_active = True
                config.last_updated = datetime.utcnow()
                
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='activate_config',
                    resource_id=config.id,
                    user_id=activated_by,
                    details={
                        'config_name': config.config_name,
                        'environment': config.environment,
                        'version': config.version
                    },
                    session=session
                )
                
                return True, []
                
        except Exception as e:
            return False, [f"Database error: {str(e)}"]
    
    def deactivate_config(self, config_id: str, deactivated_by: str = None) -> Tuple[bool, list]:
        """Deactivate a configuration"""
        try:
            with self.db_manager.get_session() as session:
                config = self.get_config_by_id(config_id, session)
                if not config:
                    return False, ["Configuration not found"]
                
                if not config.is_active:
                    return False, ["Configuration is already inactive"]
                
                config.is_active = False
                config.last_updated = datetime.utcnow()
                
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='deactivate_config',
                    resource_id=config.id,
                    user_id=deactivated_by,
                    details={
                        'config_name': config.config_name,
                        'environment': config.environment,
                        'version': config.version
                    },
                    session=session
                )
                
                return True, []
                
        except Exception as e:
            return False, [f"Database error: {str(e)}"]
    
    def clone_config(self, config_id: str, new_name: str, new_environment: str = None,
                    cloned_by: str = None) -> Tuple[OrthancConfig, list]:
        """Clone an existing configuration"""
        try:
            with self.db_manager.get_session() as session:
                original = self.get_config_by_id(config_id, session)
                if not original:
                    return None, ["Original configuration not found"]
                
                target_env = new_environment or original.environment
                
                # Check for duplicate name
                existing = self.get_config_by_name(new_name, target_env, session)
                if existing:
                    return None, [f"Configuration '{new_name}' already exists in {target_env} environment"]
                
                # Create clone
                clone = OrthancConfig(
                    config_name=new_name,
                    description=f"Cloned from {original.config_name}",
                    environment=target_env,
                    is_active=False  # Clones are always inactive by default
                )
                
                # Copy configuration data
                clone.set_config_data(original.get_config_data())
                
                # Validate
                errors = clone.validate()
                if errors:
                    return None, errors
                
                session.add(clone)
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='clone_config',
                    resource_id=clone.id,
                    user_id=cloned_by,
                    details={
                        'original_config_id': config_id,
                        'original_config_name': original.config_name,
                        'new_config_name': new_name,
                        'new_environment': target_env
                    },
                    session=session
                )
                
                return clone, []
                
        except Exception as e:
            return None, [f"Database error: {str(e)}"]
    
    def delete_config(self, config_id: str, deleted_by: str = None,
                     force: bool = False) -> Tuple[bool, list]:
        """Delete a configuration"""
        try:
            with self.db_manager.get_session() as session:
                config = self.get_config_by_id(config_id, session)
                if not config:
                    return False, ["Configuration not found"]
                
                if config.is_active and not force:
                    return False, ["Cannot delete active configuration. Use force=True to override."]
                
                config_details = {
                    'config_name': config.config_name,
                    'environment': config.environment,
                    'version': config.version,
                    'was_active': config.is_active
                }
                
                session.delete(config)
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='delete_config',
                    resource_id=config_id,
                    user_id=deleted_by,
                    details=config_details,
                    session=session
                )
                
                return True, []
                
        except Exception as e:
            return False, [f"Database error: {str(e)}"]
    
    def export_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Export configuration as JSON"""
        try:
            config = self.get_config_by_id(config_id)
            if not config:
                return None
            
            return {
                'config_name': config.config_name,
                'description': config.description,
                'environment': config.environment,
                'version': config.version,
                'config_data': config.get_config_data(),
                'created_at': config.created_at.isoformat() if config.created_at else None,
                'last_updated': config.last_updated.isoformat() if config.last_updated else None,
                'exported_at': datetime.utcnow().isoformat()
            }
            
        except Exception:
            return None
    
    def import_config(self, import_data: Dict[str, Any], imported_by: str = None,
                     overwrite: bool = False) -> Tuple[OrthancConfig, list]:
        """Import configuration from JSON"""
        try:
            config_name = import_data.get('config_name')
            environment = import_data.get('environment', 'production')
            
            if not config_name:
                return None, ["config_name is required"]
            
            with self.db_manager.get_session() as session:
                # Check for existing config
                existing = self.get_config_by_name(config_name, environment, session)
                if existing and not overwrite:
                    return None, [f"Configuration '{config_name}' already exists. Use overwrite=True to replace."]
                
                if existing and overwrite:
                    # Update existing
                    existing.description = import_data.get('description', existing.description)
                    existing.set_config_data(import_data.get('config_data', {}))
                    existing.version += 1
                    existing.last_updated = datetime.utcnow()
                    
                    errors = existing.validate()
                    if errors:
                        return None, errors
                    
                    session.commit()
                    
                    # Create audit log
                    self._create_audit_log(
                        action='import_config',
                        resource_id=existing.id,
                        user_id=imported_by,
                        details={
                            'config_name': config_name,
                            'environment': environment,
                            'overwrite': True,
                            'new_version': existing.version
                        },
                        session=session
                    )
                    
                    return existing, []
                
                else:
                    # Create new
                    config = OrthancConfig(
                        config_name=config_name,
                        description=import_data.get('description', 'Imported configuration'),
                        environment=environment,
                        is_active=False  # Imported configs are inactive by default
                    )
                    
                    config.set_config_data(import_data.get('config_data', {}))
                    
                    errors = config.validate()
                    if errors:
                        return None, errors
                    
                    session.add(config)
                    session.commit()
                    
                    # Create audit log
                    self._create_audit_log(
                        action='import_config',
                        resource_id=config.id,
                        user_id=imported_by,
                        details={
                            'config_name': config_name,
                            'environment': environment,
                            'overwrite': False
                        },
                        session=session
                    )
                    
                    return config, []
                    
        except Exception as e:
            return None, [f"Import error: {str(e)}"]
    
    def get_config_history(self, config_name: str, environment: str = 'production') -> List[Dict[str, Any]]:
        """Get configuration change history from audit logs"""
        try:
            with self.db_manager.get_session() as session:
                # Get all configs with this name/environment
                configs = session.query(OrthancConfig).filter(
                    and_(
                        OrthancConfig.config_name == config_name,
                        OrthancConfig.environment == environment
                    )
                ).order_by(desc(OrthancConfig.version)).all()
                
                if not configs:
                    return []
                
                # Get audit logs for these configs
                config_ids = [c.id for c in configs]
                
                audit_logs = session.query(AuditLog).filter(
                    and_(
                        AuditLog.resource_type == 'config',
                        AuditLog.resource_id.in_(config_ids),
                        AuditLog.action.in_(['create_config', 'update_config', 'activate_config', 'deactivate_config'])
                    )
                ).order_by(desc(AuditLog.timestamp)).all()
                
                # Combine config info with audit logs
                history = []
                for log in audit_logs:
                    config = next((c for c in configs if c.id == log.resource_id), None)
                    if config:
                        history.append({
                            'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                            'action': log.get_action_display(),
                            'version': config.version,
                            'user_id': log.user_id,
                            'details': log.get_details(),
                            'is_active': config.is_active
                        })
                
                return history
                
        except Exception:
            return []
    
    def validate_orthanc_config(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate Orthanc configuration data"""
        return OrthancConfig.validate_orthanc_config(config_data)
    
    def get_environments(self) -> List[str]:
        """Get list of all environments"""
        try:
            with self.db_manager.get_session() as session:
                result = session.query(OrthancConfig.environment).distinct().all()
                return [env[0] for env in result]
        except Exception:
            return []
    
    def get_config_statistics(self) -> Dict[str, Any]:
        """Get configuration statistics"""
        try:
            with self.db_manager.get_session() as session:
                total = session.query(OrthancConfig).count()
                active = session.query(OrthancConfig).filter(OrthancConfig.is_active == True).count()
                
                # Environment breakdown
                env_stats = session.query(
                    OrthancConfig.environment,
                    func.count(OrthancConfig.id).label('count'),
                    func.sum(func.cast(OrthancConfig.is_active, func.INTEGER)).label('active_count')
                ).group_by(OrthancConfig.environment).all()
                
                environments = {}
                for env, count, active_count in env_stats:
                    environments[env] = {
                        'total': count,
                        'active': active_count or 0
                    }
                
                return {
                    'total_configurations': total,
                    'active_configurations': active,
                    'environments': environments
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    def _deactivate_other_configs(self, environment: str, session: Session, exclude_id: str = None):
        """Deactivate all other configs in the environment"""
        query = session.query(OrthancConfig).filter(
            and_(
                OrthancConfig.environment == environment,
                OrthancConfig.is_active == True
            )
        )
        
        if exclude_id:
            query = query.filter(OrthancConfig.id != exclude_id)
        
        configs = query.all()
        for config in configs:
            config.is_active = False
            config.last_updated = datetime.utcnow()
    
    def _create_audit_log(self, action: str, resource_id: str, user_id: str = None,
                         details: Dict[str, Any] = None, session: Session = None):
        """Create audit log entry"""
        if not session:
            return
        
        try:
            audit_log = AuditLog(
                user_id=user_id,
                user_type='admin',  # Assume admin for config management
                action=action,
                resource_type='config',
                resource_id=resource_id,
                compliance_category='security'
            )
            
            if details:
                audit_log.set_details(details)
            
            session.add(audit_log)
            # Don't commit here - let parent transaction handle it
            
        except Exception:
            # Don't fail the main operation if audit logging fails
            pass

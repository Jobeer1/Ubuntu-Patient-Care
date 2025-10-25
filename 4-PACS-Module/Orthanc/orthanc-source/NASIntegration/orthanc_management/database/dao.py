"""
Data Access Objects (DAOs) for Orthanc Management Module
Provides high-level database operations with automatic SQL generation
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

from connection_manager import DatabaseManager, DatabaseConnection
from schema_generator import DatabaseType


@dataclass
class QueryResult:
    """Standardized query result wrapper"""
    success: bool
    data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    error: Optional[str] = None
    affected_rows: int = 0
    
    @classmethod
    def success_result(cls, data: Any = None, affected_rows: int = 0) -> 'QueryResult':
        return cls(success=True, data=data, affected_rows=affected_rows)
    
    @classmethod
    def error_result(cls, error: str) -> 'QueryResult':
        return cls(success=False, error=error)


class BaseDAO(ABC):
    """Base Data Access Object with common database operations"""
    
    def __init__(self, connection_name: Optional[str] = None):
        self.connection_name = connection_name
        self.table_name = self._get_table_name()
    
    @abstractmethod
    def _get_table_name(self) -> str:
        """Return the table name for this DAO"""
        pass
    
    def _get_connection(self) -> DatabaseConnection:
        """Get database connection"""
        return DatabaseManager.get_connection(self.connection_name)
    
    def _get_placeholder(self, count: int = 1) -> str:
        """Get parameter placeholders for the database type"""
        connection = self._get_connection()
        placeholder = connection.get_placeholder()
        
        if placeholder == "$":
            # PostgreSQL uses $1, $2, etc.
            return ", ".join([f"${i+1}" for i in range(count)])
        else:
            # MySQL, SQLite, Firebird use ? or %s
            return ", ".join([placeholder] * count)
    
    def _build_where_clause(self, conditions: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """Build WHERE clause from conditions dictionary"""
        if not conditions:
            return "", []
        
        placeholders = []
        values = []
        
        for key, value in conditions.items():
            if value is None:
                placeholders.append(f"{key} IS NULL")
            elif isinstance(value, (list, tuple)):
                # IN clause
                placeholder_list = self._get_placeholder(len(value))
                placeholders.append(f"{key} IN ({placeholder_list})")
                values.extend(value)
            elif isinstance(value, dict) and 'operator' in value:
                # Custom operator (e.g., {'operator': '>', 'value': 100})
                op = value['operator']
                val = value['value']
                placeholders.append(f"{key} {op} {self._get_placeholder()}")
                values.append(val)
            else:
                placeholders.append(f"{key} = {self._get_placeholder()}")
                values.append(value)
        
        where_clause = " WHERE " + " AND ".join(placeholders)
        return where_clause, values
    
    async def find_by_id(self, id_value: str) -> QueryResult:
        """Find record by ID"""
        try:
            connection = self._get_connection()
            
            query = f"SELECT * FROM {self.table_name} WHERE id = {self._get_placeholder()}"
            result = await connection.fetch_one(query, (id_value,))
            
            return QueryResult.success_result(result)
            
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def find_all(self, conditions: Optional[Dict[str, Any]] = None, 
                      limit: Optional[int] = None, 
                      offset: Optional[int] = None,
                      order_by: Optional[str] = None) -> QueryResult:
        """Find all records matching conditions"""
        try:
            connection = self._get_connection()
            
            query = f"SELECT * FROM {self.table_name}"
            params = []
            
            if conditions:
                where_clause, where_params = self._build_where_clause(conditions)
                query += where_clause
                params.extend(where_params)
            
            if order_by:
                query += f" ORDER BY {order_by}"
            
            if limit:
                query += f" LIMIT {limit}"
                if offset:
                    query += f" OFFSET {offset}"
            
            results = await connection.fetch_all(query, tuple(params) if params else None)
            
            return QueryResult.success_result(results)
            
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def create(self, data: Dict[str, Any]) -> QueryResult:
        """Create new record"""
        try:
            connection = self._get_connection()
            
            # Generate ID if not provided
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            
            # Add timestamps
            if 'created_at' not in data:
                data['created_at'] = datetime.now()
            
            columns = list(data.keys())
            placeholders = self._get_placeholder(len(columns))
            values = list(data.values())
            
            query = f"""
                INSERT INTO {self.table_name} ({', '.join(columns)})
                VALUES ({placeholders})
            """
            
            affected_rows = await connection.execute(query, tuple(values))
            
            return QueryResult.success_result(data, affected_rows)
            
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def update(self, id_value: str, data: Dict[str, Any]) -> QueryResult:
        """Update record by ID"""
        try:
            connection = self._get_connection()
            
            # Add update timestamp
            data['updated_at'] = datetime.now()
            
            set_clauses = []
            values = []
            
            for key, value in data.items():
                set_clauses.append(f"{key} = {self._get_placeholder()}")
                values.append(value)
            
            values.append(id_value)  # For WHERE clause
            
            query = f"""
                UPDATE {self.table_name}
                SET {', '.join(set_clauses)}
                WHERE id = {self._get_placeholder()}
            """
            
            affected_rows = await connection.execute(query, tuple(values))
            
            if affected_rows == 0:
                return QueryResult.error_result(f"Record with ID {id_value} not found")
            
            # Return updated record
            updated_record = await self.find_by_id(id_value)
            return QueryResult.success_result(updated_record.data, affected_rows)
            
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def delete(self, id_value: str) -> QueryResult:
        """Delete record by ID"""
        try:
            connection = self._get_connection()
            
            query = f"DELETE FROM {self.table_name} WHERE id = {self._get_placeholder()}"
            affected_rows = await connection.execute(query, (id_value,))
            
            if affected_rows == 0:
                return QueryResult.error_result(f"Record with ID {id_value} not found")
            
            return QueryResult.success_result(affected_rows=affected_rows)
            
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def count(self, conditions: Optional[Dict[str, Any]] = None) -> QueryResult:
        """Count records matching conditions"""
        try:
            connection = self._get_connection()
            
            query = f"SELECT COUNT(*) as count FROM {self.table_name}"
            params = []
            
            if conditions:
                where_clause, where_params = self._build_where_clause(conditions)
                query += where_clause
                params.extend(where_params)
            
            result = await connection.fetch_one(query, tuple(params) if params else None)
            
            return QueryResult.success_result(result['count'])
            
        except Exception as e:
            return QueryResult.error_result(str(e))


class ReferringDoctorDAO(BaseDAO):
    """Data Access Object for referring doctors"""
    
    def _get_table_name(self) -> str:
        return "referring_doctors"
    
    async def find_by_hpcsa_number(self, hpcsa_number: str) -> QueryResult:
        """Find doctor by HPCSA number"""
        try:
            connection = self._get_connection()
            query = f"SELECT * FROM {self.table_name} WHERE hpcsa_number = {self._get_placeholder()}"
            result = await connection.fetch_one(query, (hpcsa_number,))
            return QueryResult.success_result(result)
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def find_by_email(self, email: str) -> QueryResult:
        """Find doctor by email"""
        try:
            connection = self._get_connection()
            query = f"SELECT * FROM {self.table_name} WHERE email = {self._get_placeholder()}"
            result = await connection.fetch_one(query, (email,))
            return QueryResult.success_result(result)
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def find_active_doctors(self) -> QueryResult:
        """Find all active doctors"""
        return await self.find_all(conditions={'is_active': True})
    
    async def find_by_province(self, province: str) -> QueryResult:
        """Find doctors by province"""
        return await self.find_all(conditions={'province': province, 'is_active': True})
    
    async def update_last_access(self, doctor_id: str) -> QueryResult:
        """Update doctor's last access timestamp"""
        return await self.update(doctor_id, {'last_access': datetime.now()})


class PatientReferralDAO(BaseDAO):
    """Data Access Object for patient referrals"""
    
    def _get_table_name(self) -> str:
        return "patient_referrals"
    
    async def find_by_doctor(self, doctor_id: str) -> QueryResult:
        """Find referrals by referring doctor"""
        return await self.find_all(
            conditions={'referring_doctor_id': doctor_id},
            order_by="referral_date DESC"
        )
    
    async def find_by_patient(self, patient_id: str) -> QueryResult:
        """Find referrals by patient"""
        return await self.find_all(
            conditions={'patient_id': patient_id},
            order_by="referral_date DESC"
        )
    
    async def find_by_study(self, study_instance_uid: str) -> QueryResult:
        """Find referral by study UID"""
        return await self.find_all(conditions={'study_instance_uid': study_instance_uid})
    
    async def find_pending_referrals(self) -> QueryResult:
        """Find all pending referrals"""
        return await self.find_all(
            conditions={'status': 'pending'},
            order_by="referral_date ASC"
        )
    
    async def update_status(self, referral_id: str, status: str) -> QueryResult:
        """Update referral status"""
        return await self.update(referral_id, {'status': status, 'updated_at': datetime.now()})
    
    async def grant_access(self, referral_id: str, expires_hours: int = 72) -> QueryResult:
        """Grant access to referral with expiration"""
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        return await self.update(referral_id, {
            'access_granted': True,
            'access_expires': expires_at,
            'status': 'authorized'
        })


class PatientAuthorizationDAO(BaseDAO):
    """Data Access Object for patient authorizations"""
    
    def _get_table_name(self) -> str:
        return "patient_authorizations"
    
    async def find_doctor_authorizations(self, doctor_id: str, active_only: bool = True) -> QueryResult:
        """Find all authorizations for a doctor"""
        conditions = {'doctor_id': doctor_id}
        if active_only:
            conditions['is_active'] = True
        
        return await self.find_all(conditions=conditions, order_by="granted_at DESC")
    
    async def find_patient_authorizations(self, patient_id: str) -> QueryResult:
        """Find all authorizations for a patient"""
        return await self.find_all(
            conditions={'patient_id': patient_id, 'is_active': True},
            order_by="granted_at DESC"
        )
    
    async def check_access(self, doctor_id: str, patient_id: str, study_uid: str) -> QueryResult:
        """Check if doctor has access to specific patient study"""
        try:
            connection = self._get_connection()
            
            query = f"""
                SELECT * FROM {self.table_name}
                WHERE doctor_id = {self._get_placeholder()}
                  AND patient_id = {self._get_placeholder()}
                  AND (study_instance_uid = {self._get_placeholder()} OR study_instance_uid IS NULL)
                  AND is_active = true
                  AND (expires_at IS NULL OR expires_at > {self._get_placeholder()})
            """
            
            now = datetime.now()
            result = await connection.fetch_one(query, (doctor_id, patient_id, study_uid, now))
            
            return QueryResult.success_result(result)
            
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def record_access(self, authorization_id: str) -> QueryResult:
        """Record an access event"""
        try:
            connection = self._get_connection()
            
            # Update access count and last accessed
            query = f"""
                UPDATE {self.table_name}
                SET access_count = access_count + 1,
                    last_accessed = {self._get_placeholder()}
                WHERE id = {self._get_placeholder()}
            """
            
            affected_rows = await connection.execute(query, (datetime.now(), authorization_id))
            return QueryResult.success_result(affected_rows=affected_rows)
            
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def expire_authorization(self, authorization_id: str) -> QueryResult:
        """Manually expire an authorization"""
        return await self.update(authorization_id, {
            'is_active': False,
            'expires_at': datetime.now()
        })


class PatientShareDAO(BaseDAO):
    """Data Access Object for patient shares"""
    
    def _get_table_name(self) -> str:
        return "patient_shares"
    
    async def find_by_token(self, share_token: str) -> QueryResult:
        """Find share by token"""
        try:
            connection = self._get_connection()
            query = f"SELECT * FROM {self.table_name} WHERE share_token = {self._get_placeholder()}"
            result = await connection.fetch_one(query, (share_token,))
            return QueryResult.success_result(result)
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def find_by_patient(self, patient_id: str) -> QueryResult:
        """Find shares by patient"""
        return await self.find_all(
            conditions={'patient_id': patient_id},
            order_by="created_at DESC"
        )
    
    async def find_active_shares(self) -> QueryResult:
        """Find all active shares"""
        try:
            connection = self._get_connection()
            
            query = f"""
                SELECT * FROM {self.table_name}
                WHERE is_active = true
                  AND (expires_at IS NULL OR expires_at > {self._get_placeholder()})
                ORDER BY created_at DESC
            """
            
            results = await connection.fetch_all(query, (datetime.now(),))
            return QueryResult.success_result(results)
            
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def record_access(self, share_id: str, access_details: Dict[str, Any]) -> QueryResult:
        """Record share access"""
        try:
            connection = self._get_connection()
            
            # Get current share data
            share_result = await self.find_by_id(share_id)
            if not share_result.success:
                return share_result
            
            share = share_result.data
            
            # Update access log
            access_log = json.loads(share.get('access_log', '[]'))
            access_log.append({
                'timestamp': datetime.now().isoformat(),
                **access_details
            })
            
            # Update record
            return await self.update(share_id, {
                'access_count': share['access_count'] + 1,
                'last_accessed': datetime.now(),
                'access_log': json.dumps(access_log)
            })
            
        except Exception as e:
            return QueryResult.error_result(str(e))
    
    async def record_download(self, share_id: str) -> QueryResult:
        """Record a download event"""
        try:
            connection = self._get_connection()
            
            query = f"""
                UPDATE {self.table_name}
                SET download_count = download_count + 1
                WHERE id = {self._get_placeholder()}
                  AND (max_downloads IS NULL OR download_count < max_downloads)
            """
            
            affected_rows = await connection.execute(query, (share_id,))
            
            if affected_rows == 0:
                return QueryResult.error_result("Download limit exceeded or share not found")
            
            return QueryResult.success_result(affected_rows=affected_rows)
            
        except Exception as e:
            return QueryResult.error_result(str(e))


class AuditLogDAO(BaseDAO):
    """Data Access Object for audit logs"""
    
    def _get_table_name(self) -> str:
        return "audit_logs"
    
    async def log_action(self, user_id: str, action: str, **kwargs) -> QueryResult:
        """Log an audit action"""
        audit_data = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'action': action,
            'timestamp': datetime.now(),
            **kwargs
        }
        
        return await self.create(audit_data)
    
    async def find_user_actions(self, user_id: str, limit: int = 100) -> QueryResult:
        """Find actions by user"""
        return await self.find_all(
            conditions={'user_id': user_id},
            order_by="timestamp DESC",
            limit=limit
        )
    
    async def find_patient_access_logs(self, patient_id: str) -> QueryResult:
        """Find all access logs for a patient"""
        return await self.find_all(
            conditions={'patient_id': patient_id},
            order_by="timestamp DESC"
        )
    
    async def find_study_access_logs(self, study_instance_uid: str) -> QueryResult:
        """Find all access logs for a study"""
        return await self.find_all(
            conditions={'study_instance_uid': study_instance_uid},
            order_by="timestamp DESC"
        )
    
    async def compliance_report(self, start_date: datetime, end_date: datetime) -> QueryResult:
        """Generate compliance report for date range"""
        try:
            connection = self._get_connection()
            
            query = f"""
                SELECT 
                    user_type,
                    action,
                    COUNT(*) as action_count,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT patient_id) as unique_patients
                FROM {self.table_name}
                WHERE timestamp >= {self._get_placeholder()}
                  AND timestamp <= {self._get_placeholder()}
                GROUP BY user_type, action
                ORDER BY action_count DESC
            """
            
            results = await connection.fetch_all(query, (start_date, end_date))
            return QueryResult.success_result(results)
            
        except Exception as e:
            return QueryResult.error_result(str(e))


# Factory for creating DAOs
class DAOFactory:
    """Factory for creating DAO instances"""
    
    _dao_classes = {
        'referring_doctors': ReferringDoctorDAO,
        'patient_referrals': PatientReferralDAO,
        'patient_authorizations': PatientAuthorizationDAO,
        'patient_shares': PatientShareDAO,
        'audit_logs': AuditLogDAO,
    }
    
    @classmethod
    def create_dao(cls, table_name: str, connection_name: Optional[str] = None) -> BaseDAO:
        """Create DAO instance for specified table"""
        if table_name not in cls._dao_classes:
            raise ValueError(f"No DAO class found for table: {table_name}")
        
        dao_class = cls._dao_classes[table_name]
        return dao_class(connection_name)
    
    @classmethod
    def get_referring_doctor_dao(cls, connection_name: Optional[str] = None) -> ReferringDoctorDAO:
        return cls.create_dao('referring_doctors', connection_name)
    
    @classmethod
    def get_patient_referral_dao(cls, connection_name: Optional[str] = None) -> PatientReferralDAO:
        return cls.create_dao('patient_referrals', connection_name)
    
    @classmethod
    def get_patient_authorization_dao(cls, connection_name: Optional[str] = None) -> PatientAuthorizationDAO:
        return cls.create_dao('patient_authorizations', connection_name)
    
    @classmethod
    def get_patient_share_dao(cls, connection_name: Optional[str] = None) -> PatientShareDAO:
        return cls.create_dao('patient_shares', connection_name)
    
    @classmethod
    def get_audit_log_dao(cls, connection_name: Optional[str] = None) -> AuditLogDAO:
        return cls.create_dao('audit_logs', connection_name)


if __name__ == "__main__":
    # Example usage
    async def example_usage():
        # This would be used after database connections are set up
        
        # Create a referring doctor
        doctor_dao = DAOFactory.get_referring_doctor_dao()
        
        doctor_data = {
            'name': 'Dr. Example',
            'hpcsa_number': 'HP99999',
            'email': 'example@doctor.com',
            'specialization': 'General Practice',
            'province': 'Gauteng'
        }
        
        result = await doctor_dao.create(doctor_data)
        if result.success:
            print(f"Created doctor: {result.data}")
        else:
            print(f"Error: {result.error}")
    
    print("DAO system ready for use with database connections")

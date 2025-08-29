"""
Multi-Database Schema Generator for Orthanc Management Module
Supports MySQL, PostgreSQL, SQLite, Firebird, SQL Server, and Oracle
"""

from typing import Dict, List, Optional, Union, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import json


class DatabaseType(Enum):
    """Supported database types"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql" 
    SQLITE = "sqlite"
    FIREBIRD = "firebird"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"


class ColumnType(Enum):
    """Universal column types that map to database-specific types"""
    VARCHAR_50 = "varchar_50"
    VARCHAR_100 = "varchar_100"
    VARCHAR_255 = "varchar_255"
    TEXT = "text"
    LONGTEXT = "longtext"
    INTEGER = "integer"
    BIGINT = "bigint"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    DATETIME = "datetime"
    DATE = "date"
    DECIMAL = "decimal"
    FLOAT = "float"
    BLOB = "blob"
    JSON = "json"


@dataclass
class Column:
    """Universal column definition"""
    name: str
    type: ColumnType
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    default: Optional[str] = None
    auto_increment: bool = False
    foreign_key: Optional[str] = None  # Format: "table.column"
    check_constraint: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class Index:
    """Universal index definition"""
    name: str
    columns: List[str]
    unique: bool = False
    type: Optional[str] = None  # btree, hash, etc.


@dataclass
class Table:
    """Universal table definition"""
    name: str
    columns: List[Column]
    indexes: List[Index] = None
    comment: Optional[str] = None
    
    def __post_init__(self):
        if self.indexes is None:
            self.indexes = []


class DatabaseSchemaGenerator:
    """Generates database-specific SQL schema from universal definitions"""
    
    def __init__(self, db_type: DatabaseType):
        self.db_type = db_type
        self.type_mappings = self._get_type_mappings()
        self.syntax = self._get_syntax_rules()
    
    def _get_type_mappings(self) -> Dict[ColumnType, str]:
        """Get database-specific type mappings"""
        mappings = {
            DatabaseType.MYSQL: {
                ColumnType.VARCHAR_50: "VARCHAR(50)",
                ColumnType.VARCHAR_100: "VARCHAR(100)",
                ColumnType.VARCHAR_255: "VARCHAR(255)",
                ColumnType.TEXT: "TEXT",
                ColumnType.LONGTEXT: "LONGTEXT",
                ColumnType.INTEGER: "INT",
                ColumnType.BIGINT: "BIGINT",
                ColumnType.BOOLEAN: "BOOLEAN",
                ColumnType.TIMESTAMP: "TIMESTAMP",
                ColumnType.DATETIME: "DATETIME",
                ColumnType.DATE: "DATE",
                ColumnType.DECIMAL: "DECIMAL(10,2)",
                ColumnType.FLOAT: "FLOAT",
                ColumnType.BLOB: "BLOB",
                ColumnType.JSON: "JSON"
            },
            DatabaseType.POSTGRESQL: {
                ColumnType.VARCHAR_50: "VARCHAR(50)",
                ColumnType.VARCHAR_100: "VARCHAR(100)",
                ColumnType.VARCHAR_255: "VARCHAR(255)",
                ColumnType.TEXT: "TEXT",
                ColumnType.LONGTEXT: "TEXT",
                ColumnType.INTEGER: "INTEGER",
                ColumnType.BIGINT: "BIGINT",
                ColumnType.BOOLEAN: "BOOLEAN",
                ColumnType.TIMESTAMP: "TIMESTAMP",
                ColumnType.DATETIME: "TIMESTAMP",
                ColumnType.DATE: "DATE",
                ColumnType.DECIMAL: "DECIMAL(10,2)",
                ColumnType.FLOAT: "REAL",
                ColumnType.BLOB: "BYTEA",
                ColumnType.JSON: "JSONB"
            },
            DatabaseType.SQLITE: {
                ColumnType.VARCHAR_50: "TEXT",
                ColumnType.VARCHAR_100: "TEXT",
                ColumnType.VARCHAR_255: "TEXT",
                ColumnType.TEXT: "TEXT",
                ColumnType.LONGTEXT: "TEXT",
                ColumnType.INTEGER: "INTEGER",
                ColumnType.BIGINT: "INTEGER",
                ColumnType.BOOLEAN: "INTEGER",
                ColumnType.TIMESTAMP: "TEXT",
                ColumnType.DATETIME: "TEXT",
                ColumnType.DATE: "TEXT",
                ColumnType.DECIMAL: "REAL",
                ColumnType.FLOAT: "REAL",
                ColumnType.BLOB: "BLOB",
                ColumnType.JSON: "TEXT"
            },
            DatabaseType.FIREBIRD: {
                ColumnType.VARCHAR_50: "VARCHAR(50)",
                ColumnType.VARCHAR_100: "VARCHAR(100)",
                ColumnType.VARCHAR_255: "VARCHAR(255)",
                ColumnType.TEXT: "BLOB SUB_TYPE TEXT",
                ColumnType.LONGTEXT: "BLOB SUB_TYPE TEXT",
                ColumnType.INTEGER: "INTEGER",
                ColumnType.BIGINT: "BIGINT",
                ColumnType.BOOLEAN: "BOOLEAN",
                ColumnType.TIMESTAMP: "TIMESTAMP",
                ColumnType.DATETIME: "TIMESTAMP",
                ColumnType.DATE: "DATE",
                ColumnType.DECIMAL: "DECIMAL(10,2)",
                ColumnType.FLOAT: "FLOAT",
                ColumnType.BLOB: "BLOB",
                ColumnType.JSON: "BLOB SUB_TYPE TEXT"
            },
            DatabaseType.SQLSERVER: {
                ColumnType.VARCHAR_50: "NVARCHAR(50)",
                ColumnType.VARCHAR_100: "NVARCHAR(100)",
                ColumnType.VARCHAR_255: "NVARCHAR(255)",
                ColumnType.TEXT: "NVARCHAR(MAX)",
                ColumnType.LONGTEXT: "NVARCHAR(MAX)",
                ColumnType.INTEGER: "INT",
                ColumnType.BIGINT: "BIGINT",
                ColumnType.BOOLEAN: "BIT",
                ColumnType.TIMESTAMP: "DATETIME2",
                ColumnType.DATETIME: "DATETIME2",
                ColumnType.DATE: "DATE",
                ColumnType.DECIMAL: "DECIMAL(10,2)",
                ColumnType.FLOAT: "FLOAT",
                ColumnType.BLOB: "VARBINARY(MAX)",
                ColumnType.JSON: "NVARCHAR(MAX)"
            },
            DatabaseType.ORACLE: {
                ColumnType.VARCHAR_50: "VARCHAR2(50)",
                ColumnType.VARCHAR_100: "VARCHAR2(100)",
                ColumnType.VARCHAR_255: "VARCHAR2(255)",
                ColumnType.TEXT: "CLOB",
                ColumnType.LONGTEXT: "CLOB",
                ColumnType.INTEGER: "NUMBER(10)",
                ColumnType.BIGINT: "NUMBER(19)",
                ColumnType.BOOLEAN: "NUMBER(1)",
                ColumnType.TIMESTAMP: "TIMESTAMP",
                ColumnType.DATETIME: "TIMESTAMP",
                ColumnType.DATE: "DATE",
                ColumnType.DECIMAL: "NUMBER(10,2)",
                ColumnType.FLOAT: "BINARY_FLOAT",
                ColumnType.BLOB: "BLOB",
                ColumnType.JSON: "CLOB"
            }
        }
        return mappings[self.db_type]
    
    def _get_syntax_rules(self) -> Dict[str, Any]:
        """Get database-specific syntax rules"""
        syntax_rules = {
            DatabaseType.MYSQL: {
                "quote_char": "`",
                "auto_increment": "AUTO_INCREMENT",
                "current_timestamp": "CURRENT_TIMESTAMP",
                "boolean_true": "TRUE",
                "boolean_false": "FALSE",
                "supports_json": True,
                "supports_check_constraints": True,
                "cascade_syntax": "ON DELETE CASCADE ON UPDATE CASCADE"
            },
            DatabaseType.POSTGRESQL: {
                "quote_char": '"',
                "auto_increment": "GENERATED ALWAYS AS IDENTITY",
                "current_timestamp": "CURRENT_TIMESTAMP",
                "boolean_true": "TRUE",
                "boolean_false": "FALSE",
                "supports_json": True,
                "supports_check_constraints": True,
                "cascade_syntax": "ON DELETE CASCADE ON UPDATE CASCADE"
            },
            DatabaseType.SQLITE: {
                "quote_char": '"',
                "auto_increment": "AUTOINCREMENT",
                "current_timestamp": "CURRENT_TIMESTAMP",
                "boolean_true": "1",
                "boolean_false": "0",
                "supports_json": False,
                "supports_check_constraints": True,
                "cascade_syntax": "ON DELETE CASCADE ON UPDATE CASCADE"
            },
            DatabaseType.FIREBIRD: {
                "quote_char": '"',
                "auto_increment": "GENERATED BY DEFAULT AS IDENTITY",
                "current_timestamp": "CURRENT_TIMESTAMP",
                "boolean_true": "TRUE",
                "boolean_false": "FALSE",
                "supports_json": False,
                "supports_check_constraints": True,
                "cascade_syntax": "ON DELETE CASCADE ON UPDATE CASCADE"
            },
            DatabaseType.SQLSERVER: {
                "quote_char": "[",
                "quote_char_end": "]",
                "auto_increment": "IDENTITY(1,1)",
                "current_timestamp": "GETDATE()",
                "boolean_true": "1",
                "boolean_false": "0",
                "supports_json": True,
                "supports_check_constraints": True,
                "cascade_syntax": "ON DELETE CASCADE ON UPDATE CASCADE"
            },
            DatabaseType.ORACLE: {
                "quote_char": '"',
                "auto_increment": "GENERATED ALWAYS AS IDENTITY",
                "current_timestamp": "CURRENT_TIMESTAMP",
                "boolean_true": "1",
                "boolean_false": "0",
                "supports_json": True,
                "supports_check_constraints": True,
                "cascade_syntax": "ON DELETE CASCADE"
            }
        }
        return syntax_rules[self.db_type]
    
    def quote_identifier(self, identifier: str) -> str:
        """Quote database identifiers according to database rules"""
        quote_char = self.syntax["quote_char"]
        quote_char_end = self.syntax.get("quote_char_end", quote_char)
        return f"{quote_char}{identifier}{quote_char_end}"
    
    def generate_column_definition(self, column: Column) -> str:
        """Generate column definition SQL"""
        parts = []
        
        # Column name and type
        col_name = self.quote_identifier(column.name)
        col_type = self.type_mappings[column.type]
        parts.append(f"{col_name} {col_type}")
        
        # Primary key and auto increment
        if column.primary_key:
            parts.append("PRIMARY KEY")
            if column.auto_increment:
                if self.db_type == DatabaseType.MYSQL:
                    parts.append("AUTO_INCREMENT")
                elif self.db_type == DatabaseType.POSTGRESQL:
                    # PostgreSQL uses SERIAL or GENERATED ALWAYS AS IDENTITY
                    pass  # Already handled in type mapping
                elif self.db_type == DatabaseType.SQLITE:
                    parts.append("AUTOINCREMENT")
                elif self.db_type == DatabaseType.FIREBIRD:
                    # Firebird uses GENERATED BY DEFAULT AS IDENTITY
                    pass  # Already handled in type mapping
                elif self.db_type == DatabaseType.SQLSERVER:
                    parts.append("IDENTITY(1,1)")
                elif self.db_type == DatabaseType.ORACLE:
                    # Oracle uses GENERATED ALWAYS AS IDENTITY
                    pass  # Already handled in type mapping
        
        # Nullable
        if not column.nullable:
            parts.append("NOT NULL")
        
        # Unique constraint
        if column.unique and not column.primary_key:
            parts.append("UNIQUE")
        
        # Default value
        if column.default is not None:
            if column.default == "CURRENT_TIMESTAMP":
                parts.append(f"DEFAULT {self.syntax['current_timestamp']}")
            elif column.type == ColumnType.BOOLEAN:
                if column.default.lower() == "true":
                    parts.append(f"DEFAULT {self.syntax['boolean_true']}")
                else:
                    parts.append(f"DEFAULT {self.syntax['boolean_false']}")
            else:
                parts.append(f"DEFAULT '{column.default}'")
        
        # Check constraint
        if column.check_constraint and self.syntax["supports_check_constraints"]:
            parts.append(f"CHECK ({column.check_constraint})")
        
        return " ".join(parts)
    
    def generate_table_sql(self, table: Table) -> List[str]:
        """Generate CREATE TABLE SQL statements"""
        statements = []
        
        # Main CREATE TABLE statement
        table_name = self.quote_identifier(table.name)
        sql_parts = [f"CREATE TABLE {table_name} ("]
        
        # Column definitions
        column_defs = []
        foreign_keys = []
        
        for column in table.columns:
            column_def = self.generate_column_definition(column)
            column_defs.append(f"    {column_def}")
            
            # Collect foreign key constraints
            if column.foreign_key:
                foreign_keys.append(column)
        
        sql_parts.extend(column_defs)
        
        # Add foreign key constraints
        for fk_column in foreign_keys:
            ref_table, ref_column = fk_column.foreign_key.split('.')
            fk_name = f"fk_{table.name}_{fk_column.name}"
            fk_constraint = (
                f"    CONSTRAINT {self.quote_identifier(fk_name)} "
                f"FOREIGN KEY ({self.quote_identifier(fk_column.name)}) "
                f"REFERENCES {self.quote_identifier(ref_table)}({self.quote_identifier(ref_column)}) "
                f"{self.syntax['cascade_syntax']}"
            )
            sql_parts.append(fk_constraint)
        
        # Close CREATE TABLE
        sql_parts.append(");")
        
        # Join with commas
        table_sql = sql_parts[0] + "\n" + ",\n".join(sql_parts[1:-1]) + "\n" + sql_parts[-1]
        statements.append(table_sql)
        
        # Add table comment if supported
        if table.comment and self.db_type in [DatabaseType.MYSQL, DatabaseType.POSTGRESQL]:
            comment_sql = f"COMMENT ON TABLE {table_name} IS '{table.comment}';"
            statements.append(comment_sql)
        
        # Create indexes
        for index in table.indexes:
            index_sql = self.generate_index_sql(table.name, index)
            statements.append(index_sql)
        
        return statements
    
    def generate_index_sql(self, table_name: str, index: Index) -> str:
        """Generate CREATE INDEX SQL"""
        index_type = "UNIQUE " if index.unique else ""
        table_name_quoted = self.quote_identifier(table_name)
        index_name_quoted = self.quote_identifier(index.name)
        columns_quoted = [self.quote_identifier(col) for col in index.columns]
        columns_str = ", ".join(columns_quoted)
        
        return f"CREATE {index_type}INDEX {index_name_quoted} ON {table_name_quoted} ({columns_str});"
    
    def generate_sequence_sql(self, table_name: str, column_name: str) -> List[str]:
        """Generate sequences for databases that require them (Oracle, PostgreSQL)"""
        statements = []
        
        if self.db_type == DatabaseType.ORACLE:
            seq_name = f"seq_{table_name}_{column_name}"
            statements.append(f"CREATE SEQUENCE {self.quote_identifier(seq_name)} START WITH 1 INCREMENT BY 1;")
        
        return statements


def get_orthanc_management_schema() -> List[Table]:
    """Define the complete Orthanc Management Module schema"""
    
    tables = []
    
    # Referring Doctors Table
    referring_doctors = Table(
        name="referring_doctors",
        comment="Healthcare professionals who refer patients for imaging",
        columns=[
            Column("id", ColumnType.VARCHAR_50, nullable=False, primary_key=True),
            Column("name", ColumnType.VARCHAR_100, nullable=False),
            Column("hpcsa_number", ColumnType.VARCHAR_50, unique=True),
            Column("email", ColumnType.VARCHAR_100),
            Column("phone", ColumnType.VARCHAR_50),
            Column("practice_name", ColumnType.VARCHAR_100),
            Column("specialization", ColumnType.VARCHAR_100),
            Column("facility_type", ColumnType.VARCHAR_50),
            Column("province", ColumnType.VARCHAR_50),
            Column("access_level", ColumnType.VARCHAR_50, default="view_only"),
            Column("is_active", ColumnType.BOOLEAN, default="true"),
            Column("created_at", ColumnType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
            Column("last_access", ColumnType.TIMESTAMP),
            Column("referral_patterns", ColumnType.JSON),  # Analytics data
            Column("notification_preferences", ColumnType.JSON),
        ],
        indexes=[
            Index("idx_referring_doctors_hpcsa", ["hpcsa_number"], unique=True),
            Index("idx_referring_doctors_email", ["email"]),
            Index("idx_referring_doctors_active", ["is_active"]),
            Index("idx_referring_doctors_province", ["province"]),
        ]
    )
    tables.append(referring_doctors)
    
    # Patient Referrals Table
    patient_referrals = Table(
        name="patient_referrals",
        comment="Tracks patient referrals and associated studies",
        columns=[
            Column("id", ColumnType.VARCHAR_50, nullable=False, primary_key=True),
            Column("patient_id", ColumnType.VARCHAR_100, nullable=False),
            Column("patient_name", ColumnType.VARCHAR_100),
            Column("referring_doctor_id", ColumnType.VARCHAR_50, nullable=False, 
                  foreign_key="referring_doctors.id"),
            Column("study_instance_uid", ColumnType.VARCHAR_255),
            Column("accession_number", ColumnType.VARCHAR_100),
            Column("referral_date", ColumnType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
            Column("study_type", ColumnType.VARCHAR_100),
            Column("modality", ColumnType.VARCHAR_50),
            Column("clinical_indication", ColumnType.TEXT),
            Column("priority", ColumnType.VARCHAR_50, default="routine"),
            Column("status", ColumnType.VARCHAR_50, default="pending"),
            Column("access_granted", ColumnType.BOOLEAN, default="false"),
            Column("access_expires", ColumnType.TIMESTAMP),
            Column("notification_sent", ColumnType.BOOLEAN, default="false"),
            Column("patient_contacted", ColumnType.BOOLEAN, default="false"),
            Column("created_at", ColumnType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
            Column("updated_at", ColumnType.TIMESTAMP),
        ],
        indexes=[
            Index("idx_patient_referrals_doctor", ["referring_doctor_id"]),
            Index("idx_patient_referrals_patient", ["patient_id"]),
            Index("idx_patient_referrals_study", ["study_instance_uid"]),
            Index("idx_patient_referrals_accession", ["accession_number"]),
            Index("idx_patient_referrals_status", ["status"]),
            Index("idx_patient_referrals_date", ["referral_date"]),
        ]
    )
    tables.append(patient_referrals)
    
    # Patient Authorizations Table
    patient_authorizations = Table(
        name="patient_authorizations",
        comment="Controls doctor access to specific patient studies",
        columns=[
            Column("id", ColumnType.VARCHAR_50, nullable=False, primary_key=True),
            Column("doctor_id", ColumnType.VARCHAR_50, nullable=False, 
                  foreign_key="referring_doctors.id"),
            Column("patient_id", ColumnType.VARCHAR_100, nullable=False),
            Column("study_instance_uid", ColumnType.VARCHAR_255),
            Column("series_instance_uid", ColumnType.VARCHAR_255),
            Column("access_level", ColumnType.VARCHAR_50, default="view_only"),
            Column("granted_by", ColumnType.VARCHAR_50, nullable=False),
            Column("granted_at", ColumnType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
            Column("expires_at", ColumnType.TIMESTAMP),
            Column("is_active", ColumnType.BOOLEAN, default="true"),
            Column("access_count", ColumnType.INTEGER, default="0"),
            Column("last_accessed", ColumnType.TIMESTAMP),
            Column("purpose", ColumnType.TEXT),
            Column("restrictions", ColumnType.JSON),  # Access restrictions
            Column("audit_trail", ColumnType.JSON),   # Access history
        ],
        indexes=[
            Index("idx_patient_auth_doctor", ["doctor_id"]),
            Index("idx_patient_auth_patient", ["patient_id"]),
            Index("idx_patient_auth_study", ["study_instance_uid"]),
            Index("idx_patient_auth_active", ["is_active"]),
            Index("idx_patient_auth_expires", ["expires_at"]),
            Index("idx_patient_auth_combo", ["doctor_id", "patient_id", "study_instance_uid"], unique=True),
        ]
    )
    tables.append(patient_authorizations)
    
    # Patient Shares Table
    patient_shares = Table(
        name="patient_shares",
        comment="Secure sharing links for patients to access their images",
        columns=[
            Column("id", ColumnType.VARCHAR_50, nullable=False, primary_key=True),
            Column("patient_id", ColumnType.VARCHAR_100, nullable=False),
            Column("patient_name", ColumnType.VARCHAR_100),
            Column("patient_email", ColumnType.VARCHAR_100),
            Column("patient_phone", ColumnType.VARCHAR_50),
            Column("study_uids", ColumnType.TEXT),  # JSON array of study UIDs
            Column("series_uids", ColumnType.TEXT), # JSON array of series UIDs
            Column("share_token", ColumnType.VARCHAR_255, nullable=False, unique=True),
            Column("password_hash", ColumnType.VARCHAR_255),
            Column("created_by", ColumnType.VARCHAR_50, nullable=False),
            Column("created_at", ColumnType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
            Column("expires_at", ColumnType.TIMESTAMP),
            Column("max_downloads", ColumnType.INTEGER, default="10"),
            Column("download_count", ColumnType.INTEGER, default="0"),
            Column("access_count", ColumnType.INTEGER, default="0"),
            Column("last_accessed", ColumnType.TIMESTAMP),
            Column("is_active", ColumnType.BOOLEAN, default="true"),
            Column("mobile_optimized", ColumnType.BOOLEAN, default="true"),
            Column("download_permissions", ColumnType.JSON),
            Column("access_log", ColumnType.JSON),  # Detailed access history
            Column("notification_history", ColumnType.JSON),
        ],
        indexes=[
            Index("idx_patient_shares_token", ["share_token"], unique=True),
            Index("idx_patient_shares_patient", ["patient_id"]),
            Index("idx_patient_shares_email", ["patient_email"]),
            Index("idx_patient_shares_expires", ["expires_at"]),
            Index("idx_patient_shares_active", ["is_active"]),
            Index("idx_patient_shares_created", ["created_at"]),
        ]
    )
    tables.append(patient_shares)
    
    # Orthanc Configuration Table
    orthanc_configs = Table(
        name="orthanc_configs",
        comment="Dynamic Orthanc server configuration management",
        columns=[
            Column("id", ColumnType.VARCHAR_50, nullable=False, primary_key=True),
            Column("config_name", ColumnType.VARCHAR_100, nullable=False),
            Column("description", ColumnType.TEXT),
            Column("config_data", ColumnType.LONGTEXT),  # JSON configuration
            Column("config_version", ColumnType.VARCHAR_50),
            Column("environment", ColumnType.VARCHAR_50, default="production"),
            Column("is_active", ColumnType.BOOLEAN, default="false"),
            Column("is_default", ColumnType.BOOLEAN, default="false"),
            Column("created_by", ColumnType.VARCHAR_50),
            Column("created_at", ColumnType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
            Column("applied_at", ColumnType.TIMESTAMP),
            Column("backup_config", ColumnType.LONGTEXT), # Previous config backup
            Column("validation_status", ColumnType.VARCHAR_50),
            Column("validation_errors", ColumnType.TEXT),
        ],
        indexes=[
            Index("idx_orthanc_config_name", ["config_name"]),
            Index("idx_orthanc_config_active", ["is_active"]),
            Index("idx_orthanc_config_default", ["is_default"]),
            Index("idx_orthanc_config_env", ["environment"]),
            Index("idx_orthanc_config_version", ["config_version"]),
        ]
    )
    tables.append(orthanc_configs)
    
    # Orthanc Server Status Table
    orthanc_server_status = Table(
        name="orthanc_server_status",
        comment="Real-time Orthanc server monitoring and metrics",
        columns=[
            Column("id", ColumnType.INTEGER, nullable=False, primary_key=True, auto_increment=True),
            Column("timestamp", ColumnType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
            Column("server_status", ColumnType.VARCHAR_50),  # running, stopped, error
            Column("process_id", ColumnType.INTEGER),
            Column("http_port", ColumnType.INTEGER),
            Column("dicom_port", ColumnType.INTEGER),
            Column("cpu_usage", ColumnType.FLOAT),
            Column("memory_usage", ColumnType.BIGINT),
            Column("disk_usage", ColumnType.BIGINT),
            Column("active_connections", ColumnType.INTEGER),
            Column("studies_count", ColumnType.INTEGER),
            Column("series_count", ColumnType.INTEGER),
            Column("instances_count", ColumnType.INTEGER),
            Column("storage_size", ColumnType.BIGINT),
            Column("error_count", ColumnType.INTEGER),
            Column("last_error", ColumnType.TEXT),
            Column("configuration_hash", ColumnType.VARCHAR_255),
            Column("uptime_seconds", ColumnType.BIGINT),
            Column("performance_metrics", ColumnType.JSON),
        ],
        indexes=[
            Index("idx_server_status_timestamp", ["timestamp"]),
            Index("idx_server_status_status", ["server_status"]),
            Index("idx_server_status_process", ["process_id"]),
        ]
    )
    tables.append(orthanc_server_status)
    
    # Comprehensive Audit Log Table
    audit_logs = Table(
        name="audit_logs",
        comment="Comprehensive audit trail for HPCSA/POPIA compliance",
        columns=[
            Column("id", ColumnType.VARCHAR_50, nullable=False, primary_key=True),
            Column("timestamp", ColumnType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
            Column("user_id", ColumnType.VARCHAR_50),
            Column("user_type", ColumnType.VARCHAR_50),  # admin, doctor, patient, system
            Column("user_name", ColumnType.VARCHAR_100),
            Column("hpcsa_number", ColumnType.VARCHAR_50),
            Column("action", ColumnType.VARCHAR_100, nullable=False),
            Column("resource_type", ColumnType.VARCHAR_50),  # study, patient, config, etc.
            Column("resource_id", ColumnType.VARCHAR_255),
            Column("patient_id", ColumnType.VARCHAR_100),
            Column("study_instance_uid", ColumnType.VARCHAR_255),
            Column("details", ColumnType.LONGTEXT),  # JSON details
            Column("ip_address", ColumnType.VARCHAR_45),
            Column("user_agent", ColumnType.TEXT),
            Column("session_id", ColumnType.VARCHAR_100),
            Column("success", ColumnType.BOOLEAN, default="true"),
            Column("error_message", ColumnType.TEXT),
            Column("compliance_flags", ColumnType.JSON),  # HPCSA/POPIA markers
            Column("retention_date", ColumnType.DATE),  # Data retention policy
        ],
        indexes=[
            Index("idx_audit_timestamp", ["timestamp"]),
            Index("idx_audit_user", ["user_id"]),
            Index("idx_audit_hpcsa", ["hpcsa_number"]),
            Index("idx_audit_action", ["action"]),
            Index("idx_audit_resource", ["resource_type", "resource_id"]),
            Index("idx_audit_patient", ["patient_id"]),
            Index("idx_audit_study", ["study_instance_uid"]),
            Index("idx_audit_session", ["session_id"]),
            Index("idx_audit_retention", ["retention_date"]),
        ]
    )
    tables.append(audit_logs)
    
    # Notification Queue Table
    notification_queue = Table(
        name="notification_queue",
        comment="Queue for email/SMS notifications",
        columns=[
            Column("id", ColumnType.VARCHAR_50, nullable=False, primary_key=True),
            Column("recipient_type", ColumnType.VARCHAR_50),  # doctor, patient, admin
            Column("recipient_id", ColumnType.VARCHAR_50),
            Column("recipient_email", ColumnType.VARCHAR_100),
            Column("recipient_phone", ColumnType.VARCHAR_50),
            Column("notification_type", ColumnType.VARCHAR_50),  # study_ready, link_created, etc.
            Column("subject", ColumnType.VARCHAR_255),
            Column("message", ColumnType.TEXT),
            Column("message_html", ColumnType.LONGTEXT),
            Column("language", ColumnType.VARCHAR_10, default="en"),
            Column("priority", ColumnType.VARCHAR_50, default="normal"),
            Column("status", ColumnType.VARCHAR_50, default="pending"),
            Column("attempts", ColumnType.INTEGER, default="0"),
            Column("max_attempts", ColumnType.INTEGER, default="3"),
            Column("created_at", ColumnType.TIMESTAMP, default="CURRENT_TIMESTAMP"),
            Column("scheduled_at", ColumnType.TIMESTAMP),
            Column("sent_at", ColumnType.TIMESTAMP),
            Column("error_message", ColumnType.TEXT),
            Column("metadata", ColumnType.JSON),  # Additional context
        ],
        indexes=[
            Index("idx_notification_status", ["status"]),
            Index("idx_notification_scheduled", ["scheduled_at"]),
            Index("idx_notification_recipient", ["recipient_type", "recipient_id"]),
            Index("idx_notification_type", ["notification_type"]),
            Index("idx_notification_priority", ["priority"]),
        ]
    )
    tables.append(notification_queue)
    
    return tables


if __name__ == "__main__":
    # Example usage - generate schema for different databases
    schema_tables = get_orthanc_management_schema()
    
    # Generate for MySQL
    mysql_generator = DatabaseSchemaGenerator(DatabaseType.MYSQL)
    print("=== MySQL Schema ===")
    for table in schema_tables:
        statements = mysql_generator.generate_table_sql(table)
        for stmt in statements:
            print(stmt)
            print()
    
    # Generate for Firebird
    firebird_generator = DatabaseSchemaGenerator(DatabaseType.FIREBIRD)
    print("\n=== Firebird Schema ===")
    for table in schema_tables:
        statements = firebird_generator.generate_table_sql(table)
        for stmt in statements:
            print(stmt)
            print()

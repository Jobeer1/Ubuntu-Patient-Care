import sqlite3
from typing import List, Optional, Dict
from .models import MedicalDevice
from .config import DB_PATH
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def get_connection(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class DeviceRepository:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medical_devices (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    modality_type TEXT NOT NULL,
                    manufacturer TEXT NOT NULL,
                    model TEXT NOT NULL,
                    ae_title TEXT NOT NULL UNIQUE,
                    ip_address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    department TEXT NOT NULL,
                    location TEXT NOT NULL,
                    serial_number TEXT,
                    installation_date TEXT,
                    last_service_date TEXT,
                    status TEXT DEFAULT 'active',
                    notes TEXT,
                    created_date TEXT NOT NULL,
                    updated_date TEXT NOT NULL
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_connectivity_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    test_date TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    response_time_ms INTEGER,
                    error_message TEXT,
                    FOREIGN KEY (device_id) REFERENCES medical_devices (id)
                )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_modality ON medical_devices(modality_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_department ON medical_devices(department)')
            conn.commit()

    def add_device(self, device: MedicalDevice) -> None:
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO medical_devices (id, name, modality_type, manufacturer, model, ae_title, ip_address, port,
                                            department, location, serial_number, installation_date, last_service_date,
                                            status, notes, created_date, updated_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device.id, device.name, device.modality_type, device.manufacturer, device.model,
                device.ae_title, device.ip_address, device.port, device.department, device.location,
                device.serial_number, device.installation_date, device.last_service_date, device.status,
                device.notes, device.created_date, device.updated_date
            ))
            conn.commit()

    def get_device_by_id(self, device_id: str) -> Optional[MedicalDevice]:
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM medical_devices WHERE id = ?', (device_id,))
            row = cursor.fetchone()
            if row:
                return MedicalDevice.from_dict(dict(row))
            return None

    def get_device_by_ae_title(self, ae_title: str) -> Optional[MedicalDevice]:
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM medical_devices WHERE ae_title = ?', (ae_title,))
            row = cursor.fetchone()
            if row:
                return MedicalDevice.from_dict(dict(row))
            return None

    def update_device(self, device_id: str, updates: Dict) -> bool:
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            set_clauses = ', '.join([f"{k} = ?" for k in updates.keys()])
            params = list(updates.values()) + [device_id]
            cursor.execute(f"UPDATE medical_devices SET {set_clauses} WHERE id = ?", params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_device(self, device_id: str) -> bool:
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM medical_devices WHERE id = ?', (device_id,))
            cursor.execute('DELETE FROM device_connectivity_tests WHERE device_id = ?', (device_id,))
            conn.commit()
            return True

    def list_devices(self, status: str = None, modality_type: str = None, department: str = None) -> List[MedicalDevice]:
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            query = 'SELECT * FROM medical_devices WHERE 1=1'
            params = []
            if status:
                query += ' AND status = ?'
                params.append(status)
            if modality_type:
                query += ' AND modality_type = ?'
                params.append(modality_type)
            if department:
                query += ' AND department = ?'
                params.append(department)
            query += ' ORDER BY name'
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [MedicalDevice.from_dict(dict(r)) for r in rows]

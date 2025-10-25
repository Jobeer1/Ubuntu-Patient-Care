"""
Image Database Management for Orthanc NAS Integration
Handles DICOM image metadata, user associations, and sharing
"""

import sqlite3
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import logging
import os

@dataclass
class DicomImage:
    """DICOM image metadata class"""
    image_id: str
    orthanc_id: str  # Orthanc instance ID
    study_id: str
    series_id: str
    patient_id: str
    patient_name: str
    study_date: str
    study_time: str
    modality: str
    study_description: str
    series_description: str
    institution_name: str
    referring_physician: str
    nas_path: str  # Path on NAS
    file_size: int
    file_hash: str  # SHA-256 hash for integrity
    owner_user_id: str  # User who uploaded/owns the image
    created_at: str
    updated_at: str
    tags: str = ""  # JSON array of tags
    is_shared: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Parse JSON fields
        if self.tags:
            try:
                data['tags'] = json.loads(self.tags)
            except:
                data['tags'] = []
        else:
            data['tags'] = []
        return data

@dataclass
class SharedLink:
    """Shared link for DICOM images"""
    link_id: str
    image_id: str
    created_by: str
    recipient_email: str
    access_token: str
    expires_at: str
    max_views: int
    current_views: int
    is_active: bool
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

class ImageDatabase:
    """Image database management class"""
    
    def __init__(self, db_path: str = "orthanc_images.db"):
        self.db_path = db_path
        self.logger = self._setup_logging()
        self._init_database()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for image database operations"""
        logger = logging.getLogger('image_db')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_database(self):
        """Initialize the image database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # DICOM images table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dicom_images (
                image_id TEXT PRIMARY KEY,
                orthanc_id TEXT UNIQUE NOT NULL,
                study_id TEXT NOT NULL,
                series_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                study_date TEXT,
                study_time TEXT,
                modality TEXT,
                study_description TEXT,
                series_description TEXT,
                institution_name TEXT,
                referring_physician TEXT,
                nas_path TEXT NOT NULL,
                file_size INTEGER,
                file_hash TEXT,
                owner_user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags TEXT DEFAULT '[]',
                is_shared BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Shared links table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_links (
                link_id TEXT PRIMARY KEY,
                image_id TEXT NOT NULL,
                created_by TEXT NOT NULL,
                recipient_email TEXT,
                access_token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                max_views INTEGER DEFAULT -1,
                current_views INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (image_id) REFERENCES dicom_images (image_id)
            )
        ''')
        
        # Image access log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS image_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id TEXT NOT NULL,
                user_id TEXT,
                access_token TEXT,
                ip_address TEXT,
                user_agent TEXT,
                access_type TEXT,  -- 'view', 'download', 'share'
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (image_id) REFERENCES dicom_images (image_id)
            )
        ''')
        
        # Image tags table (for better tag management)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS image_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                tag_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (image_id) REFERENCES dicom_images (image_id),
                UNIQUE(image_id, tag_name)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_owner ON dicom_images(owner_user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_study ON dicom_images(study_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_patient ON dicom_images(patient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_modality ON dicom_images(modality)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_date ON dicom_images(study_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shared_links_token ON shared_links(access_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_access_log_image ON image_access_log(image_id)')
        
        conn.commit()
        conn.close()
    
    def _generate_image_id(self) -> str:
        """Generate unique image ID"""
        return f"img_{secrets.token_hex(8)}"
    
    def _generate_link_id(self) -> str:
        """Generate unique link ID"""
        return f"link_{secrets.token_hex(8)}"
    
    def _generate_access_token(self) -> str:
        """Generate secure access token"""
        return secrets.token_urlsafe(32)
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate file hash: {e}")
            return ""
    
    def add_image(self, image: DicomImage) -> bool:
        """Add new DICOM image to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Set timestamps
            now = datetime.now().isoformat()
            image.created_at = now
            image.updated_at = now
            
            cursor.execute('''
                INSERT INTO dicom_images (
                    image_id, orthanc_id, study_id, series_id, patient_id, patient_name,
                    study_date, study_time, modality, study_description, series_description,
                    institution_name, referring_physician, nas_path, file_size, file_hash,
                    owner_user_id, created_at, updated_at, tags, is_shared
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                image.image_id, image.orthanc_id, image.study_id, image.series_id,
                image.patient_id, image.patient_name, image.study_date, image.study_time,
                image.modality, image.study_description, image.series_description,
                image.institution_name, image.referring_physician, image.nas_path,
                image.file_size, image.file_hash, image.owner_user_id,
                image.created_at, image.updated_at, image.tags, image.is_shared
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Image added: {image.image_id} (Patient: {image.patient_name})")
            return True
            
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Image add failed - integrity error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Image add failed: {e}")
            return False
    
    def get_image_by_id(self, image_id: str) -> Optional[DicomImage]:
        """Get image by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM dicom_images WHERE image_id = ?', (image_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return DicomImage(*row)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get image by ID {image_id}: {e}")
            return None
    
    def get_image_by_orthanc_id(self, orthanc_id: str) -> Optional[DicomImage]:
        """Get image by Orthanc ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM dicom_images WHERE orthanc_id = ?', (orthanc_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return DicomImage(*row)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get image by Orthanc ID {orthanc_id}: {e}")
            return None
    
    def get_user_images(self, user_id: str, limit: int = 100, offset: int = 0) -> List[DicomImage]:
        """Get images owned by user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM dicom_images 
                WHERE owner_user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [DicomImage(*row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Failed to get user images for {user_id}: {e}")
            return []
    
    def search_images(self, user_id: str = None, filters: Dict[str, Any] = None, 
                     limit: int = 100, offset: int = 0) -> List[DicomImage]:
        """Search images with filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT * FROM dicom_images WHERE 1=1"
            params = []
            
            # User filter (for non-admin users)
            if user_id:
                query += " AND owner_user_id = ?"
                params.append(user_id)
            
            # Apply filters
            if filters:
                if 'patient_name' in filters:
                    query += " AND patient_name LIKE ?"
                    params.append(f"%{filters['patient_name']}%")
                
                if 'patient_id' in filters:
                    query += " AND patient_id LIKE ?"
                    params.append(f"%{filters['patient_id']}%")
                
                if 'modality' in filters:
                    query += " AND modality = ?"
                    params.append(filters['modality'])
                
                if 'study_date_from' in filters:
                    query += " AND study_date >= ?"
                    params.append(filters['study_date_from'])
                
                if 'study_date_to' in filters:
                    query += " AND study_date <= ?"
                    params.append(filters['study_date_to'])
                
                if 'study_description' in filters:
                    query += " AND study_description LIKE ?"
                    params.append(f"%{filters['study_description']}%")
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [DicomImage(*row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Failed to search images: {e}")
            return []
    
    def update_image(self, image: DicomImage) -> bool:
        """Update image information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            image.updated_at = datetime.now().isoformat()
            
            cursor.execute('''
                UPDATE dicom_images SET
                    patient_name = ?, study_description = ?, series_description = ?,
                    institution_name = ?, referring_physician = ?, tags = ?,
                    is_shared = ?, updated_at = ?
                WHERE image_id = ?
            ''', (
                image.patient_name, image.study_description, image.series_description,
                image.institution_name, image.referring_physician, image.tags,
                image.is_shared, image.updated_at, image.image_id
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Image updated: {image.image_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update image {image.image_id}: {e}")
            return False
    
    def delete_image(self, image_id: str) -> bool:
        """Delete image from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete related records first
            cursor.execute('DELETE FROM shared_links WHERE image_id = ?', (image_id,))
            cursor.execute('DELETE FROM image_access_log WHERE image_id = ?', (image_id,))
            cursor.execute('DELETE FROM image_tags WHERE image_id = ?', (image_id,))
            cursor.execute('DELETE FROM dicom_images WHERE image_id = ?', (image_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Image deleted: {image_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete image {image_id}: {e}")
            return False
    
    def create_shared_link(self, image_id: str, created_by: str, recipient_email: str = None,
                          expires_hours: int = 24, max_views: int = -1) -> Optional[SharedLink]:
        """Create shared link for image"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if image exists
            cursor.execute('SELECT image_id FROM dicom_images WHERE image_id = ?', (image_id,))
            if not cursor.fetchone():
                conn.close()
                return None
            
            # Create shared link
            link = SharedLink(
                link_id=self._generate_link_id(),
                image_id=image_id,
                created_by=created_by,
                recipient_email=recipient_email or "",
                access_token=self._generate_access_token(),
                expires_at=(datetime.now() + timedelta(hours=expires_hours)).isoformat(),
                max_views=max_views,
                current_views=0,
                is_active=True,
                created_at=datetime.now().isoformat()
            )
            
            cursor.execute('''
                INSERT INTO shared_links (
                    link_id, image_id, created_by, recipient_email, access_token,
                    expires_at, max_views, current_views, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                link.link_id, link.image_id, link.created_by, link.recipient_email,
                link.access_token, link.expires_at, link.max_views, link.current_views,
                link.is_active, link.created_at
            ))
            
            # Mark image as shared
            cursor.execute('''
                UPDATE dicom_images SET is_shared = TRUE WHERE image_id = ?
            ''', (image_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Shared link created: {link.link_id} for image {image_id}")
            return link
            
        except Exception as e:
            self.logger.error(f"Failed to create shared link for {image_id}: {e}")
            return None
    
    def get_shared_link_by_token(self, access_token: str) -> Optional[Tuple[SharedLink, DicomImage]]:
        """Get shared link and associated image by access token"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.*, i.*
                FROM shared_links s
                JOIN dicom_images i ON s.image_id = i.image_id
                WHERE s.access_token = ? AND s.is_active = TRUE
            ''', (access_token,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Split the row data
            link_data = row[:10]  # First 10 columns are from shared_links
            image_data = row[10:]  # Remaining columns are from dicom_images
            
            link = SharedLink(*link_data)
            image = DicomImage(*image_data)
            
            # Check if link has expired
            if datetime.fromisoformat(link.expires_at) < datetime.now():
                self.deactivate_shared_link(link.link_id)
                return None
            
            # Check view limit
            if link.max_views > 0 and link.current_views >= link.max_views:
                return None
            
            return link, image
            
        except Exception as e:
            self.logger.error(f"Failed to get shared link by token: {e}")
            return None
    
    def increment_link_views(self, link_id: str) -> bool:
        """Increment view count for shared link"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE shared_links SET current_views = current_views + 1
                WHERE link_id = ?
            ''', (link_id,))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to increment views for link {link_id}: {e}")
            return False
    
    def deactivate_shared_link(self, link_id: str) -> bool:
        """Deactivate shared link"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE shared_links SET is_active = FALSE WHERE link_id = ?
            ''', (link_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Shared link deactivated: {link_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deactivate shared link {link_id}: {e}")
            return False
    
    def get_user_shared_links(self, user_id: str) -> List[Dict[str, Any]]:
        """Get shared links created by user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.*, i.patient_name, i.study_description
                FROM shared_links s
                JOIN dicom_images i ON s.image_id = i.image_id
                WHERE s.created_by = ?
                ORDER BY s.created_at DESC
            ''', (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            links = []
            for row in rows:
                link_data = row[:10]
                patient_name = row[10]
                study_description = row[11]
                
                link = SharedLink(*link_data)
                link_dict = link.to_dict()
                link_dict['patient_name'] = patient_name
                link_dict['study_description'] = study_description
                
                links.append(link_dict)
            
            return links
            
        except Exception as e:
            self.logger.error(f"Failed to get shared links for user {user_id}: {e}")
            return []
    
    def log_image_access(self, image_id: str, user_id: str = None, access_token: str = None,
                        ip_address: str = None, user_agent: str = None, access_type: str = "view"):
        """Log image access"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO image_access_log (
                    image_id, user_id, access_token, ip_address, user_agent, access_type
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (image_id, user_id, access_token, ip_address, user_agent, access_type))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log image access: {e}")
    
    def add_image_tag(self, image_id: str, tag_name: str, tag_value: str = "") -> bool:
        """Add tag to image"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO image_tags (image_id, tag_name, tag_value)
                VALUES (?, ?, ?)
            ''', (image_id, tag_name, tag_value))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add tag to image {image_id}: {e}")
            return False
    
    def remove_image_tag(self, image_id: str, tag_name: str) -> bool:
        """Remove tag from image"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM image_tags WHERE image_id = ? AND tag_name = ?
            ''', (image_id, tag_name))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove tag from image {image_id}: {e}")
            return False
    
    def get_image_tags(self, image_id: str) -> List[Dict[str, str]]:
        """Get tags for image"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tag_name, tag_value FROM image_tags WHERE image_id = ?
            ''', (image_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{'name': row[0], 'value': row[1]} for row in rows]
            
        except Exception as e:
            self.logger.error(f"Failed to get tags for image {image_id}: {e}")
            return []
    
    def get_image_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get image statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Base query conditions
            where_clause = ""
            params = []
            
            if user_id:
                where_clause = "WHERE owner_user_id = ?"
                params.append(user_id)
            
            # Total images
            cursor.execute(f'SELECT COUNT(*) FROM dicom_images {where_clause}', params)
            total_images = cursor.fetchone()[0]
            
            # Images by modality
            cursor.execute(f'''
                SELECT modality, COUNT(*) FROM dicom_images {where_clause}
                GROUP BY modality ORDER BY COUNT(*) DESC
            ''', params)
            images_by_modality = dict(cursor.fetchall())
            
            # Recent uploads (last 7 days)
            cursor.execute(f'''
                SELECT COUNT(*) FROM dicom_images 
                {where_clause} {"AND" if where_clause else "WHERE"} 
                created_at > datetime('now', '-7 days')
            ''', params)
            recent_uploads = cursor.fetchone()[0]
            
            # Shared images
            cursor.execute(f'''
                SELECT COUNT(*) FROM dicom_images 
                {where_clause} {"AND" if where_clause else "WHERE"} is_shared = TRUE
            ''', params)
            shared_images = cursor.fetchone()[0]
            
            # Total file size
            cursor.execute(f'SELECT SUM(file_size) FROM dicom_images {where_clause}', params)
            total_size = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_images': total_images,
                'images_by_modality': images_by_modality,
                'recent_uploads_7d': recent_uploads,
                'shared_images': shared_images,
                'total_size_bytes': total_size,
                'total_size_gb': round(total_size / (1024**3), 2)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get image stats: {e}")
            return {}

# Global image database instance
image_db = ImageDatabase()
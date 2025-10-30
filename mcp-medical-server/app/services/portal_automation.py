"""
Portal Automation Tools for Medical Scheme Integration
Automated registration, login management, and bulk operations
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import sqlite3
import hashlib
import base64
from cryptography.fernet import Fernet
import os

from app.services.medical_scheme_scraper import MedicalSchemePortalScraper, SchemeStatus

logger = logging.getLogger(__name__)

@dataclass
class PortalCredentials:
    """Secure storage for portal credentials"""
    scheme_code: str
    username: str
    encrypted_password: str
    created_at: datetime
    last_used: datetime
    status: str = "active"
    notes: str = ""

@dataclass
class AutoRegistrationRequest:
    """Request for automated portal registration"""
    scheme_code: str
    practice_name: str
    practice_number: str
    contact_person: str
    email: str
    phone: str
    address: Dict[str, str]
    speciality: str
    hpcsa_number: str

class PortalCredentialsManager:
    """Secure management of medical scheme portal credentials"""
    
    def __init__(self, db_path: str = "portal_credentials.db"):
        self.db_path = db_path
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        self._init_database()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for credentials"""
        key_file = "credentials.key"
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict file permissions
            return key
    
    def _init_database(self):
        """Initialize credentials database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portal_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_code TEXT NOT NULL,
                username TEXT NOT NULL,
                encrypted_password TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                last_used TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'active',
                notes TEXT,
                UNIQUE(scheme_code, username)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_code TEXT NOT NULL,
                session_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                last_activity TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraping_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_code TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                total_time_seconds REAL DEFAULT 0,
                last_operation TIMESTAMP NOT NULL,
                average_response_time REAL DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS member_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_code TEXT NOT NULL,
                member_number TEXT NOT NULL,
                cached_data TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 0,
                UNIQUE(scheme_code, member_number)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_credentials(self, scheme_code: str, username: str, password: str, notes: str = "") -> bool:
        """Securely store portal credentials"""
        try:
            encrypted_password = self.cipher.encrypt(password.encode()).decode()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO portal_credentials 
                (scheme_code, username, encrypted_password, created_at, last_used, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                scheme_code, username, encrypted_password,
                datetime.now(), datetime.now(), notes
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Stored credentials for {scheme_code}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store credentials for {scheme_code}: {str(e)}")
            return False
    
    def get_credentials(self, scheme_code: str) -> Optional[Dict[str, str]]:
        """Retrieve and decrypt portal credentials"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, encrypted_password FROM portal_credentials 
                WHERE scheme_code = ? AND status = 'active'
                ORDER BY last_used DESC LIMIT 1
            ''', (scheme_code,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                username, encrypted_password = result
                password = self.cipher.decrypt(encrypted_password.encode()).decode()
                
                # Update last used
                self._update_last_used(scheme_code, username)
                
                return {"username": username, "password": password}
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve credentials for {scheme_code}: {str(e)}")
            return None
    
    def _update_last_used(self, scheme_code: str, username: str):
        """Update last used timestamp for credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE portal_credentials 
            SET last_used = ? 
            WHERE scheme_code = ? AND username = ?
        ''', (datetime.now(), scheme_code, username))
        
        conn.commit()
        conn.close()
    
    def list_stored_credentials(self) -> List[Dict[str, Any]]:
        """List all stored credentials (without passwords)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT scheme_code, username, created_at, last_used, status, notes
            FROM portal_credentials
            ORDER BY scheme_code, last_used DESC
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "scheme_code": row[0],
                "username": row[1],
                "created_at": row[2],
                "last_used": row[3],
                "status": row[4],
                "notes": row[5]
            })
        
        conn.close()
        return results

class MedicalSchemeAutoRegistration:
    """Automated registration for medical scheme provider portals"""
    
    def __init__(self, scraper: MedicalSchemePortalScraper):
        self.scraper = scraper
        self.registration_forms = self._load_registration_forms()
    
    def _load_registration_forms(self) -> Dict[str, Dict[str, Any]]:
        """Load registration form configurations for each scheme"""
        return {
            "DISCOVERY": {
                "registration_url": "https://www.discovery.co.za/portal/providers/register",
                "form_fields": {
                    "practice_name": "practiceName",
                    "practice_number": "practiceNumber", 
                    "contact_person": "contactPerson",
                    "email": "email",
                    "phone": "phone",
                    "address": "address",
                    "city": "city",
                    "postal_code": "postalCode",
                    "speciality": "speciality",
                    "hpcsa_number": "hpcsaNumber"
                },
                "required_documents": [
                    "HPCSA certificate",
                    "Practice registration certificate",
                    "Banking details"
                ]
            },
            
            "MOMENTUM": {
                "registration_url": "https://www.momentum.co.za/providers/register",
                "form_fields": {
                    "practice_name": "practice_name",
                    "practice_number": "practice_no",
                    "contact_person": "contact_name", 
                    "email": "email_address",
                    "phone": "phone_number",
                    "speciality": "speciality_code",
                    "hpcsa_number": "hpcsa_no"
                },
                "required_documents": [
                    "HPCSA registration",
                    "Banking details",
                    "Tax clearance certificate"
                ]
            },
            
            "BONITAS": {
                "registration_url": "https://www.bonitas.co.za/providers/application",
                "form_fields": {
                    "practice_name": "practiceName",
                    "contact_person": "contactPerson",
                    "email": "emailAddress",
                    "phone": "phoneNumber",
                    "hpcsa_number": "hpcsaNumber"
                }
            }
            
            # Add configurations for all 71 schemes
        }
    
    async def auto_register(self, request: AutoRegistrationRequest) -> Dict[str, Any]:
        """Automatically register practice with medical scheme portal"""
        try:
            scheme_code = request.scheme_code
            
            if scheme_code not in self.registration_forms:
                return {
                    "success": False,
                    "error": f"Auto-registration not supported for {scheme_code}",
                    "manual_url": f"Please register manually at scheme portal"
                }
            
            config = self.registration_forms[scheme_code]
            
            # Create browser session
            driver = await self.scraper.create_browser_session(scheme_code, headless=False)
            
            logger.info(f"🚀 Starting auto-registration for {scheme_code}...")
            
            # Navigate to registration page
            driver.get(config["registration_url"])
            await asyncio.sleep(3)
            
            # Fill registration form
            success = await self._fill_registration_form(driver, config, request)
            
            if success:
                # Submit form
                submit_button = driver.find_element(By.XPATH, 
                    "//button[@type='submit'] | //input[@type='submit'] | //button[contains(text(), 'Submit')] | //button[contains(text(), 'Register')]"
                )
                submit_button.click()
                
                # Wait for confirmation
                await asyncio.sleep(5)
                
                # Check for success message
                success_indicators = [
                    "registration successful",
                    "application submitted", 
                    "thank you for registering",
                    "confirmation number",
                    "reference number"
                ]
                
                page_text = driver.page_source.lower()
                registration_successful = any(indicator in page_text for indicator in success_indicators)
                
                if registration_successful:
                    # Extract confirmation details
                    confirmation_details = await self._extract_confirmation_details(driver)
                    
                    return {
                        "success": True,
                        "scheme_code": scheme_code,
                        "confirmation": confirmation_details,
                        "next_steps": config.get("next_steps", [
                            "Wait for approval email",
                            "Upload required documents", 
                            "Complete verification process"
                        ]),
                        "estimated_approval_time": config.get("approval_time", "5-10 business days")
                    }
                else:
                    # Check for error messages
                    error_message = await self._extract_error_message(driver)
                    
                    return {
                        "success": False,
                        "error": error_message or "Registration submission may have failed",
                        "requires_manual_intervention": True
                    }
            
            else:
                return {
                    "success": False,
                    "error": "Failed to fill registration form",
                    "requires_manual_intervention": True
                }
                
        except Exception as e:
            logger.error(f"❌ Auto-registration failed for {scheme_code}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "requires_manual_intervention": True
            }
        finally:
            await self.scraper.close_session(scheme_code)
    
    async def _fill_registration_form(self, driver, config: Dict[str, Any], request: AutoRegistrationRequest) -> bool:
        """Fill registration form with practice details"""
        try:
            form_fields = config["form_fields"]
            
            # Map request data to form fields
            field_mapping = {
                "practice_name": request.practice_name,
                "practice_number": request.practice_number,
                "contact_person": request.contact_person,
                "email": request.email,
                "phone": request.phone,
                "speciality": request.speciality,
                "hpcsa_number": request.hpcsa_number
            }
            
            # Add address fields
            if request.address:
                field_mapping.update({
                    "address": request.address.get("street", ""),
                    "city": request.address.get("city", ""),
                    "postal_code": request.address.get("postal_code", ""),
                    "province": request.address.get("province", "")
                })
            
            # Fill each form field
            for field_key, field_name in form_fields.items():
                if field_key in field_mapping and field_mapping[field_key]:
                    try:
                        # Try different selector strategies
                        selectors = [
                            f"input[name='{field_name}']",
                            f"select[name='{field_name}']", 
                            f"textarea[name='{field_name}']",
                            f"#{field_name}",
                            f".{field_name}"
                        ]
                        
                        element = None
                        for selector in selectors:
                            try:
                                element = driver.find_element(By.CSS_SELECTOR, selector)
                                break
                            except NoSuchElementException:
                                continue
                        
                        if element:
                            if element.tag_name == "select":
                                # Handle dropdown selection
                                select = Select(element)
                                try:
                                    select.select_by_visible_text(field_mapping[field_key])
                                except:
                                    select.select_by_value(field_mapping[field_key])
                            else:
                                # Handle text input
                                element.clear()
                                await self.scraper._human_type(element, field_mapping[field_key])
                            
                            logger.info(f"✅ Filled {field_key}: {field_mapping[field_key]}")
                            
                        else:
                            logger.warning(f"⚠️  Could not find field: {field_key}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️  Error filling {field_key}: {str(e)}")
                        continue
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Form filling failed: {str(e)}")
            return False
    
    async def _extract_confirmation_details(self, driver) -> Dict[str, Any]:
        """Extract registration confirmation details"""
        confirmation = {}
        
        try:
            # Look for confirmation number
            confirmation_selectors = [
                ".confirmation-number",
                ".reference-number", 
                ".application-number",
                "[class*='confirmation']",
                "[class*='reference']"
            ]
            
            for selector in confirmation_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    confirmation["reference_number"] = element.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Extract any additional details
            confirmation["timestamp"] = datetime.now().isoformat()
            confirmation["page_title"] = driver.title
            
        except Exception as e:
            logger.warning(f"Could not extract confirmation details: {str(e)}")
        
        return confirmation
    
    async def _extract_error_message(self, driver) -> Optional[str]:
        """Extract error message from registration page"""
        error_selectors = [
            ".error-message",
            ".alert-danger",
            ".validation-error",
            "[class*='error']",
            "[class*='invalid']"
        ]
        
        for selector in error_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    return element.text.strip()
            except NoSuchElementException:
                continue
        
        return None
    
    def get_registration_requirements(self, scheme_code: str) -> Dict[str, Any]:
        """Get registration requirements for a specific scheme"""
        if scheme_code not in self.registration_forms:
            return {"error": "Scheme not supported"}
        
        config = self.registration_forms[scheme_code]
        return {
            "scheme_code": scheme_code,
            "registration_url": config["registration_url"],
            "required_fields": list(config["form_fields"].keys()),
            "required_documents": config.get("required_documents", []),
            "estimated_approval_time": config.get("approval_time", "Unknown"),
            "auto_registration_supported": True
        }
    
    def get_all_registration_requirements(self) -> Dict[str, Any]:
        """Get registration requirements for all supported schemes"""
        requirements = {}
        
        for scheme_code in self.registration_forms.keys():
            requirements[scheme_code] = self.get_registration_requirements(scheme_code)
        
        # Add unsupported schemes
        all_schemes = set(self.scraper.get_supported_schemes())
        supported_schemes = set(self.registration_forms.keys())
        unsupported_schemes = all_schemes - supported_schemes
        
        for scheme_code in unsupported_schemes:
            requirements[scheme_code] = {
                "scheme_code": scheme_code,
                "auto_registration_supported": False,
                "manual_registration_required": True,
                "note": "Please register manually on scheme portal"
            }
        
        return requirements

class BulkPortalOperations:
    """Bulk operations across multiple medical scheme portals"""
    
    def __init__(self, scraper: MedicalSchemePortalScraper, credentials_manager: PortalCredentialsManager):
        self.scraper = scraper
        self.credentials_manager = credentials_manager
    
    async def bulk_member_verification(self, member_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify multiple members across different schemes
        member_list format: [{"scheme": "DISCOVERY", "member_number": "123", "id_number": "456"}]
        """
        results = {
            "total_requests": len(member_list),
            "successful_verifications": 0,
            "failed_verifications": 0,
            "results": [],
            "summary_by_scheme": {},
            "processing_time": 0
        }
        
        start_time = datetime.now()
        
        try:
            # Group by scheme for efficient processing
            scheme_groups = {}
            for member in member_list:
                scheme = member["scheme"]
                if scheme not in scheme_groups:
                    scheme_groups[scheme] = []
                scheme_groups[scheme].append(member)
            
            # Process each scheme
            for scheme_code, members in scheme_groups.items():
                scheme_results = {
                    "scheme": scheme_code,
                    "total": len(members),
                    "successful": 0,
                    "failed": 0,
                    "members": []
                }
                
                try:
                    # Get credentials for this scheme
                    credentials = self.credentials_manager.get_credentials(scheme_code)
                    if not credentials:
                        logger.warning(f"⚠️  No credentials stored for {scheme_code}")
                        for member in members:
                            scheme_results["members"].append({
                                **member,
                                "status": "failed",
                                "error": "No credentials stored"
                            })
                            scheme_results["failed"] += 1
                        continue
                    
                    # Login to portal
                    login_success = await self.scraper.login_to_portal(
                        scheme_code,
                        credentials["username"],
                        credentials["password"]
                    )
                    
                    if not login_success:
                        logger.error(f"❌ Login failed for {scheme_code}")
                        for member in members:
                            scheme_results["members"].append({
                                **member,
                                "status": "failed", 
                                "error": "Login failed"
                            })
                            scheme_results["failed"] += 1
                        continue
                    
                    # Process each member
                    for member in members:
                        try:
                            member_data = await self.scraper.search_member(
                                scheme_code,
                                member["member_number"],
                                member.get("id_number")
                            )
                            
                            if "error" not in member_data:
                                scheme_results["members"].append({
                                    **member,
                                    "status": "success",
                                    "data": member_data
                                })
                                scheme_results["successful"] += 1
                                results["successful_verifications"] += 1
                            else:
                                scheme_results["members"].append({
                                    **member,
                                    "status": "failed",
                                    "error": member_data["error"]
                                })
                                scheme_results["failed"] += 1
                                results["failed_verifications"] += 1
                            
                            # Rate limiting
                            await asyncio.sleep(self.scraper.schemes[scheme_code].rate_limit_seconds)
                            
                        except Exception as e:
                            logger.error(f"❌ Member verification failed: {str(e)}")
                            scheme_results["members"].append({
                                **member,
                                "status": "failed",
                                "error": str(e)
                            })
                            scheme_results["failed"] += 1
                            results["failed_verifications"] += 1
                
                except Exception as e:
                    logger.error(f"❌ Scheme processing failed for {scheme_code}: {str(e)}")
                    for member in members:
                        scheme_results["members"].append({
                            **member,
                            "status": "failed",
                            "error": f"Scheme processing failed: {str(e)}"
                        })
                        scheme_results["failed"] += 1
                        results["failed_verifications"] += 1
                
                results["summary_by_scheme"][scheme_code] = scheme_results
                results["results"].extend(scheme_results["members"])
        
        except Exception as e:
            logger.error(f"❌ Bulk verification failed: {str(e)}")
            results["global_error"] = str(e)
        
        finally:
            # Close all sessions
            await self.scraper.close_all_sessions()
            
            end_time = datetime.now()
            results["processing_time"] = (end_time - start_time).total_seconds()
            results["completed_at"] = end_time.isoformat()
        
        return results
    
    async def bulk_benefits_extraction(self, member_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract benefits information for multiple members"""
        results = {
            "total_requests": len(member_list),
            "successful_extractions": 0, 
            "failed_extractions": 0,
            "results": []
        }
        
        # Similar implementation to bulk_member_verification
        # but calling get_member_benefits instead
        
        return results
    
    async def monitor_portal_availability(self) -> Dict[str, Any]:
        """Monitor availability of all medical scheme portals"""
        availability_results = {
            "timestamp": datetime.now().isoformat(),
            "total_schemes": len(self.scraper.schemes),
            "available": 0,
            "unavailable": 0,
            "maintenance": 0,
            "unknown": 0,
            "details": {}
        }
        
        for scheme_code, scheme_config in self.scraper.schemes.items():
            try:
                # Simple HTTP check
                response = requests.get(scheme_config.login_url, timeout=10)
                
                if response.status_code == 200:
                    status = "available"
                    availability_results["available"] += 1
                elif response.status_code == 503:
                    status = "maintenance"
                    availability_results["maintenance"] += 1
                else:
                    status = "unavailable"
                    availability_results["unavailable"] += 1
                
                availability_results["details"][scheme_code] = {
                    "status": status,
                    "response_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
                
            except Exception as e:
                availability_results["details"][scheme_code] = {
                    "status": "unknown",
                    "error": str(e)
                }
                availability_results["unknown"] += 1
        
        return availability_results
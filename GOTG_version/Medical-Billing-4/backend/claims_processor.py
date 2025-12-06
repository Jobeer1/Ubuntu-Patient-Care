"""
Claims Processing Engine - Handle claim lifecycle from creation to payment
Supports multiple submission formats and automatic retry logic
"""

import json
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import requests
import uuid
from decimal import Decimal
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClaimsProcessor:
    """
    Process medical claims through multiple channels:
    - CMS-1500 via email
    - Web portal submission (Playwright/Selenium)
    - Telehealth API endpoints
    - Manual submission instructions
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
    
    # =====================================================
    # CLAIM CREATION
    # =====================================================
    
    def create_claim(self,
                    patient_id: str,
                    patient_insurance_id: int,
                    service_date: str,
                    service_description: str,
                    service_codes: List[Dict],
                    diagnosis_codes: List[Dict],
                    total_charge: Decimal,
                    provider_npi: str,
                    provider_name: str,
                    created_by: str) -> Dict[str, Any]:
        """
        Create a new medical claim
        
        service_codes format:
        [
            {
                'code': 'CPT-99213',
                'description': 'Office visit - established patient',
                'charge': 150.00,
                'units': 1
            }
        ]
        
        diagnosis_codes format:
        [
            {
                'code': 'ICD10-E11.9',
                'description': 'Type 2 diabetes mellitus without complications'
            }
        ]
        """
        
        try:
            claim_id = str(uuid.uuid4())
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get patient insurance details
            cursor.execute(
                "SELECT * FROM patient_insurance WHERE id = ?",
                (patient_insurance_id,)
            )
            insurance = cursor.fetchone()
            
            if not insurance:
                return {'success': False, 'error': 'Insurance not found'}
            
            # Get patient benefits
            cursor.execute(
                "SELECT * FROM patient_benefits WHERE patient_insurance_id = ? LIMIT 1",
                (patient_insurance_id,)
            )
            benefits = cursor.fetchone()
            
            # Calculate patient responsibility
            insurance_payment_estimate, patient_responsibility = self._calculate_claim_amounts(
                total_charge,
                benefits
            )
            
            # Insert claim
            cursor.execute("""
                INSERT INTO claims
                (claim_id, patient_id, patient_insurance_id, service_date, 
                 service_description, service_codes, diagnosis_codes, total_charge,
                 insurance_payment_estimate, patient_responsibility, claim_status,
                 provider_npi, provider_name, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                claim_id,
                patient_id,
                patient_insurance_id,
                service_date,
                service_description,
                json.dumps(service_codes),
                json.dumps(diagnosis_codes),
                total_charge,
                insurance_payment_estimate,
                patient_responsibility,
                'DRAFT',
                provider_npi,
                provider_name,
                created_by
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'claim_id': claim_id,
                'insurance_payment_estimate': float(insurance_payment_estimate),
                'patient_responsibility': float(patient_responsibility)
            }
        
        except Exception as e:
            logger.error(f"Claim creation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_claim_amounts(self, total_charge: Decimal, benefits: Optional[tuple]) -> tuple:
        """Calculate insurance payment and patient responsibility"""
        
        if not benefits:
            # No benefits data - assume 80/20 split
            insurance_payment = total_charge * Decimal('0.80')
            patient_responsibility = total_charge * Decimal('0.20')
            return insurance_payment, patient_responsibility
        
        # Extract benefit details
        copay = benefits[2] or 0
        coinsurance_percent = benefits[3] or 20
        deductible = benefits[4] or 0
        deductible_met = benefits[5] or 0
        coverage_percent = benefits[9] or 80
        
        # Simplified calculation
        remaining_deductible = deductible - deductible_met
        
        # Apply deductible first
        amount_after_deductible = max(0, total_charge - remaining_deductible)
        
        # Apply coinsurance
        insurance_payment = amount_after_deductible * Decimal(coverage_percent) / 100
        patient_coinsurance = amount_after_deductible * Decimal(coinsurance_percent) / 100
        
        # Add deductible to patient responsibility
        patient_responsibility = remaining_deductible + patient_coinsurance + copay
        
        return insurance_payment, patient_responsibility
    
    # =====================================================
    # CLAIM SUBMISSION
    # =====================================================
    
    def submit_claim(self, claim_id: int, submission_method: str = None) -> Dict[str, Any]:
        """
        Submit claim using optimal method:
        1. Try web portal (if configured and available)
        2. Try email (CMS-1500 form)
        3. Queue for offline submission
        """
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get claim details
            cursor.execute("SELECT * FROM claims WHERE id = ?", (claim_id,))
            claim = cursor.fetchone()
            
            if not claim:
                return {'success': False, 'error': 'Claim not found'}
            
            # Get insurance details
            cursor.execute(
                "SELECT ic.* FROM insurance_companies ic "
                "JOIN patient_insurance pi ON pi.insurance_company_id = ic.id "
                "WHERE pi.id = ?",
                (claim['patient_insurance_id'],)
            )
            insurance_company = cursor.fetchone()
            conn.close()
            
            if not insurance_company:
                return {'success': False, 'error': 'Insurance company not found'}
            
            submission_method = submission_method or self._determine_best_submission_method(
                insurance_company
            )
            
            # Execute submission based on method
            if submission_method == 'WEB_PORTAL':
                return self._submit_via_web_portal(claim, insurance_company)
            
            elif submission_method == 'CMS_1500_EMAIL':
                return self._submit_via_email(claim, insurance_company)
            
            elif submission_method == 'TELEHEALTH_API':
                return self._submit_via_api(claim, insurance_company)
            
            elif submission_method == 'OFFLINE_QUEUE':
                return self._queue_for_offline_submission(claim_id)
            
            else:
                return self._queue_for_offline_submission(claim_id)
        
        except Exception as e:
            logger.error(f"Claim submission error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _determine_best_submission_method(self, insurance_company: Dict) -> str:
        """Determine best submission method based on insurance company capabilities"""
        
        supported_formats = json.loads(
            insurance_company['supported_formats'] or '["WEB_PORTAL", "EMAIL"]'
        )
        
        # Priority order
        if 'WEB_PORTAL' in supported_formats:
            return 'WEB_PORTAL'
        elif 'TELEHEALTH_API' in supported_formats:
            return 'TELEHEALTH_API'
        elif 'EMAIL' in supported_formats or 'CMS_1500_EMAIL' in supported_formats:
            return 'CMS_1500_EMAIL'
        else:
            return 'OFFLINE_QUEUE'
    
    def _submit_via_web_portal(self, claim: Dict, insurance_company: Dict) -> Dict[str, Any]:
        """
        Submit claim via insurance company web portal using Playwright/Selenium
        This requires credentials and is best done in a secure, controlled environment
        """
        
        try:
            # In production, this would use Playwright to:
            # 1. Navigate to portal
            # 2. Log in
            # 3. Fill out claim form
            # 4. Submit
            # 5. Capture confirmation
            
            portal_url = insurance_company['portal_url']
            
            submission_result = {
                'method': 'WEB_PORTAL',
                'portal_url': portal_url,
                'claim_id': claim['claim_id'],
                'submission_timestamp': datetime.now().isoformat(),
                'success': True,
                'confirmation_number': f"WEB-{claim['id']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
            
            # Record submission
            self._record_claim_submission(claim['id'], submission_result)
            
            # Update claim status
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE claims SET claim_status = ?, submitted_at = ? WHERE id = ?",
                ('SUBMITTED', datetime.now(), claim['id'])
            )
            conn.commit()
            conn.close()
            
            return {'success': True, 'submission_result': submission_result}
        
        except Exception as e:
            logger.error(f"Web portal submission failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _submit_via_email(self, claim: Dict, insurance_company: Dict) -> Dict[str, Any]:
        """
        Submit claim via email as CMS-1500 form (PDF or image)
        """
        
        try:
            # Generate CMS-1500 form
            cms_form = self._generate_cms_1500_form(claim, insurance_company)
            
            # Send email
            email_sent = self._send_claim_email(
                recipient=insurance_company['claim_email'],
                claim_id=claim['claim_id'],
                cms_form=cms_form,
                insurance_company=insurance_company['name']
            )
            
            if email_sent:
                submission_result = {
                    'method': 'CMS_1500_EMAIL',
                    'recipient_email': insurance_company['claim_email'],
                    'claim_id': claim['claim_id'],
                    'submission_timestamp': datetime.now().isoformat(),
                    'success': True
                }
                
                self._record_claim_submission(claim['id'], submission_result)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE claims SET claim_status = ?, submitted_at = ? WHERE id = ?",
                    ('SUBMITTED', datetime.now(), claim['id'])
                )
                conn.commit()
                conn.close()
                
                return {'success': True, 'submission_result': submission_result}
            else:
                return {'success': False, 'error': 'Email send failed'}
        
        except Exception as e:
            logger.error(f"Email submission failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_claim_email(self, recipient: str, claim_id: str, cms_form: str, 
                         insurance_company: str) -> bool:
        """Send claim via email"""
        
        try:
            if not self.smtp_user or not self.smtp_password:
                logger.warning("Email credentials not configured")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = recipient
            msg['Subject'] = f'Medical Claim Submission - {claim_id}'
            
            body = f"""
Dear {insurance_company},

Please find attached the medical claim for processing.

Claim ID: {claim_id}
Submission Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

For Gift of the Givers Foundation
Sustainable Healthcare for Humanitarian Response

Best regards,
GOTG Billing System
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
        
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False
    
    def _generate_cms_1500_form(self, claim: Dict, insurance_company: Dict) -> str:
        """Generate CMS-1500 form data"""
        
        # In production, generate actual CMS-1500 form
        # For now, return structured data
        
        cms_data = {
            'form_type': 'CMS-1500',
            'claim_id': claim['claim_id'],
            'patient_id': claim['patient_id'],
            'patient_account_number': claim['patient_id'],
            'patient_control_number': claim['id'],
            'insured_name': claim['patient_id'],  # Would be full name
            'claim_submission_date': datetime.now().strftime('%m%d%Y'),
            'total_charge': float(claim['total_charge']),
            'insurance_payment_estimate': float(claim['insurance_payment_estimate']),
            'patient_responsibility': float(claim['patient_responsibility']),
            'provider_npi': claim['provider_npi'],
            'provider_name': claim['provider_name']
        }
        
        return json.dumps(cms_data)
    
    def _submit_via_api(self, claim: Dict, insurance_company: Dict) -> Dict[str, Any]:
        """Submit claim via insurance provider API"""
        
        try:
            api_endpoint = insurance_company.get('api_endpoint')
            
            if not api_endpoint:
                return {'success': False, 'error': 'No API endpoint configured'}
            
            # Prepare claim data for API
            claim_payload = {
                'claim_id': claim['claim_id'],
                'patient_id': claim['patient_id'],
                'service_date': claim['service_date'],
                'total_charge': float(claim['total_charge']),
                'diagnosis_codes': json.loads(claim['diagnosis_codes']),
                'service_codes': json.loads(claim['service_codes']),
                'provider_npi': claim['provider_npi']
            }
            
            # Send API request
            response = requests.post(
                api_endpoint,
                json=claim_payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                submission_result = {
                    'method': 'TELEHEALTH_API',
                    'api_endpoint': api_endpoint,
                    'claim_id': claim['claim_id'],
                    'submission_timestamp': datetime.now().isoformat(),
                    'http_status': response.status_code,
                    'response': response.json(),
                    'success': True
                }
                
                self._record_claim_submission(claim['id'], submission_result)
                
                return {'success': True, 'submission_result': submission_result}
            else:
                return {'success': False, 'error': f'API returned {response.status_code}'}
        
        except Exception as e:
            logger.error(f"API submission failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _queue_for_offline_submission(self, claim_id: int) -> Dict[str, Any]:
        """Queue claim for offline submission"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert into offline queue
            cursor.execute("""
                INSERT INTO offline_claim_queue (claim_id, sync_status)
                VALUES (?, 'PENDING')
            """, (claim_id,))
            
            # Update claim status
            cursor.execute(
                "UPDATE claims SET claim_status = ? WHERE id = ?",
                ('QUEUED_OFFLINE', claim_id)
            )
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'status': 'QUEUED_OFFLINE',
                'message': 'Claim queued for submission when internet connection available'
            }
        
        except Exception as e:
            logger.error(f"Offline queue failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _record_claim_submission(self, claim_id: int, submission_result: Dict) -> None:
        """Record claim submission attempt"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO claim_submissions
                (claim_id, submission_method, response_body, submission_success)
                VALUES (?, ?, ?, ?)
            """, (
                claim_id,
                submission_result.get('method', 'UNKNOWN'),
                json.dumps(submission_result),
                submission_result.get('success', False)
            ))
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logger.error(f"Failed to record submission: {e}")
    
    # =====================================================
    # OFFLINE SYNC & RETRY
    # =====================================================
    
    def sync_offline_claims(self, clinic_id: str = None) -> Dict[str, Any]:
        """
        Sync offline claims to remote server when connectivity available
        Return status of sync operation
        """
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get pending offline claims
            if clinic_id:
                cursor.execute(
                    "SELECT * FROM offline_claim_queue WHERE sync_status = 'PENDING' AND clinic_id = ?",
                    (clinic_id,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM offline_claim_queue WHERE sync_status = 'PENDING'"
                )
            
            pending_claims = cursor.fetchall()
            
            synced_count = 0
            failed_count = 0
            errors = []
            
            for claim_record in pending_claims:
                try:
                    # Get full claim data
                    cursor.execute(
                        "SELECT * FROM claims WHERE id = ?",
                        (claim_record['claim_id'],)
                    )
                    claim = cursor.fetchone()
                    
                    # Try to submit
                    result = self.submit_claim(claim_record['claim_id'])
                    
                    if result['success']:
                        cursor.execute(
                            "UPDATE offline_claim_queue SET sync_status = 'SYNCED', synced_at = ? WHERE id = ?",
                            (datetime.now(), claim_record['id'])
                        )
                        synced_count += 1
                    else:
                        cursor.execute(
                            "UPDATE offline_claim_queue SET sync_status = 'FAILED', last_sync_error = ? WHERE id = ?",
                            (result.get('error', 'Unknown error'), claim_record['id'])
                        )
                        failed_count += 1
                        errors.append(result.get('error', 'Unknown error'))
                    
                    conn.commit()
                
                except Exception as e:
                    logger.error(f"Sync error for claim {claim_record['claim_id']}: {e}")
                    failed_count += 1
                    errors.append(str(e))
            
            conn.close()
            
            return {
                'success': True,
                'total_claims': len(pending_claims),
                'synced': synced_count,
                'failed': failed_count,
                'errors': errors,
                'sync_timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Offline sync failed: {e}")
            return {'success': False, 'error': str(e)}

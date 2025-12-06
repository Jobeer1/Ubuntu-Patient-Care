"""
South African Localization Module
Provides multi-language support, local terminology, and SA-specific features
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import re

class SouthAfricanLocalization:
    """South African localization and terminology management"""
    
    def __init__(self):
        self.languages = {
            'en': 'English',
            'af': 'Afrikaans', 
            'zu': 'isiZulu'
        }
        self.default_language = 'en'
        self.translations = self._load_translations()
        self.medical_terms = self._load_medical_terms()
        self.medical_aids = self._load_medical_aids()
        self.provinces = self._load_provinces()
        
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """Load translation dictionaries"""
        return {
            'en': {
                # Authentication
                'login': 'Login',
                'logout': 'Logout',
                'username': 'Username',
                'password': 'Password',
                'pin': 'PIN',
                'forgot_password': 'Forgot Password',
                'remember_me': 'Remember Me',
                
                # Navigation
                'dashboard': 'Dashboard',
                'patients': 'Patients',
                'studies': 'Studies',
                'reports': 'Reports',
                'settings': 'Settings',
                'help': 'Help',
                
                # Medical Terms
                'patient_name': 'Patient Name',
                'patient_id': 'Patient ID',
                'date_of_birth': 'Date of Birth',
                'gender': 'Gender',
                'medical_aid': 'Medical Aid',
                'id_number': 'ID Number',
                'contact_number': 'Contact Number',
                'address': 'Address',
                
                # Imaging
                'xray': 'X-Ray',
                'ct_scan': 'CT Scan',
                'mri_scan': 'MRI Scan',
                'ultrasound': 'Ultrasound',
                'mammography': 'Mammography',
                'bone_density': 'Bone Density',
                'nuclear_medicine': 'Nuclear Medicine',
                
                # Status
                'pending': 'Pending',
                'in_progress': 'In Progress',
                'completed': 'Completed',
                'cancelled': 'Cancelled',
                'urgent': 'Urgent',
                'routine': 'Routine',
                
                # Actions
                'save': 'Save',
                'cancel': 'Cancel',
                'delete': 'Delete',
                'edit': 'Edit',
                'view': 'View',
                'print': 'Print',
                'export': 'Export',
                'share': 'Share',
                
                # Messages
                'success': 'Success',
                'error': 'Error',
                'warning': 'Warning',
                'info': 'Information',
                'loading': 'Loading...',
                'no_data': 'No data available',
                
                # Time
                'today': 'Today',
                'yesterday': 'Yesterday',
                'this_week': 'This Week',
                'this_month': 'This Month',
                'last_month': 'Last Month',
            },
            
            'af': {
                # Authentication
                'login': 'Aanmeld',
                'logout': 'Afmeld',
                'username': 'Gebruikersnaam',
                'password': 'Wagwoord',
                'pin': 'PIN',
                'forgot_password': 'Wagwoord Vergeet',
                'remember_me': 'Onthou My',
                
                # Navigation
                'dashboard': 'Beheersentrum',
                'patients': 'Pasiënte',
                'studies': 'Studies',
                'reports': 'Verslae',
                'settings': 'Instellings',
                'help': 'Hulp',
                
                # Medical Terms
                'patient_name': 'Pasiënt Naam',
                'patient_id': 'Pasiënt ID',
                'date_of_birth': 'Geboortedatum',
                'gender': 'Geslag',
                'medical_aid': 'Mediese Fonds',
                'id_number': 'ID Nommer',
                'contact_number': 'Kontak Nommer',
                'address': 'Adres',
                
                # Imaging
                'xray': 'X-Straal',
                'ct_scan': 'CT Skandering',
                'mri_scan': 'MRI Skandering',
                'ultrasound': 'Ultraklank',
                'mammography': 'Mammografie',
                'bone_density': 'Beendigtheid',
                'nuclear_medicine': 'Kernmedisyne',
                
                # Status
                'pending': 'Hangende',
                'in_progress': 'Besig',
                'completed': 'Voltooi',
                'cancelled': 'Gekanselleer',
                'urgent': 'Dringend',
                'routine': 'Roetine',
                
                # Actions
                'save': 'Stoor',
                'cancel': 'Kanselleer',
                'delete': 'Verwyder',
                'edit': 'Wysig',
                'view': 'Bekyk',
                'print': 'Druk',
                'export': 'Uitvoer',
                'share': 'Deel',
                
                # Messages
                'success': 'Sukses',
                'error': 'Fout',
                'warning': 'Waarskuwing',
                'info': 'Inligting',
                'loading': 'Laai...',
                'no_data': 'Geen data beskikbaar nie',
                
                # Time
                'today': 'Vandag',
                'yesterday': 'Gister',
                'this_week': 'Hierdie Week',
                'this_month': 'Hierdie Maand',
                'last_month': 'Verlede Maand',
            },
            
            'zu': {
                # Authentication
                'login': 'Ngena',
                'logout': 'Phuma',
                'username': 'Igama Lomsebenzisi',
                'password': 'Iphasiwedi',
                'pin': 'I-PIN',
                'forgot_password': 'Ukhohlwe Iphasiwedi',
                'remember_me': 'Ngikhumbule',
                
                # Navigation
                'dashboard': 'Ibhodi Lokulawula',
                'patients': 'Iziguli',
                'studies': 'Izifundo',
                'reports': 'Imibiko',
                'settings': 'Izilungiselelo',
                'help': 'Usizo',
                
                # Medical Terms
                'patient_name': 'Igama Lesiguli',
                'patient_id': 'I-ID Yesiguli',
                'date_of_birth': 'Usuku Lokuzalwa',
                'gender': 'Ubulili',
                'medical_aid': 'Usizo Lwezempilo',
                'id_number': 'Inombolo Yesazisi',
                'contact_number': 'Inombolo Yokuxhumana',
                'address': 'Ikheli',
                
                # Imaging
                'xray': 'I-X-Ray',
                'ct_scan': 'Ukuskena kwe-CT',
                'mri_scan': 'Ukuskena kwe-MRI',
                'ultrasound': 'I-Ultrasound',
                'mammography': 'I-Mammography',
                'bone_density': 'Ukujiya Kwamathambo',
                'nuclear_medicine': 'Imithi Ye-Nuclear',
                
                # Status
                'pending': 'Kulindile',
                'in_progress': 'Kuyaqhubeka',
                'completed': 'Kuqediwe',
                'cancelled': 'Kukhanseliwe',
                'urgent': 'Kuphuthumayo',
                'routine': 'Okuvamile',
                
                # Actions
                'save': 'Gcina',
                'cancel': 'Khansela',
                'delete': 'Susa',
                'edit': 'Hlela',
                'view': 'Buka',
                'print': 'Phrinta',
                'export': 'Khipha',
                'share': 'Yabelana',
                
                # Messages
                'success': 'Impumelelo',
                'error': 'Iphutha',
                'warning': 'Isexwayiso',
                'info': 'Ulwazi',
                'loading': 'Iyalayisha...',
                'no_data': 'Alikho idatha',
                
                # Time
                'today': 'Namuhla',
                'yesterday': 'Izolo',
                'this_week': 'Kuleli Viki',
                'this_month': 'Kuleli Nyanga',
                'last_month': 'Inyanga Edlule',
            }
        }
    
    def _load_medical_terms(self) -> Dict[str, Dict[str, str]]:
        """Load South African medical terminology"""
        return {
            'modalities': {
                'CR': 'Computed Radiography',
                'CT': 'Computed Tomography',
                'MR': 'Magnetic Resonance',
                'US': 'Ultrasound',
                'XA': 'X-Ray Angiography',
                'RF': 'Radiofluoroscopy',
                'DX': 'Digital Radiography',
                'MG': 'Mammography',
                'NM': 'Nuclear Medicine',
                'PT': 'Positron Emission Tomography',
                'DXA': 'Dual-energy X-ray Absorptiometry',
                'BMD': 'Bone Mineral Density'
            },
            'body_parts': {
                'CHEST': 'Chest',
                'ABDOMEN': 'Abdomen',
                'PELVIS': 'Pelvis',
                'HEAD': 'Head',
                'NECK': 'Neck',
                'SPINE': 'Spine',
                'EXTREMITY': 'Extremity',
                'HEART': 'Heart',
                'BRAIN': 'Brain',
                'LIVER': 'Liver',
                'KIDNEY': 'Kidney',
                'LUNG': 'Lung'
            },
            'procedures': {
                'ROUTINE': 'Routine Examination',
                'CONTRAST': 'Contrast Study',
                'EMERGENCY': 'Emergency Study',
                'FOLLOW_UP': 'Follow-up Study',
                'SCREENING': 'Screening Study',
                'BIOPSY': 'Biopsy Guidance',
                'INTERVENTION': 'Interventional Procedure'
            }
        }
    
    def _load_medical_aids(self) -> Dict[str, Dict[str, Any]]:
        """Load South African medical aid schemes"""
        return {
            'discovery': {
                'name': 'Discovery Health',
                'code': 'DISC',
                'contact': '0860 99 88 77',
                'website': 'www.discovery.co.za',
                'plans': ['Executive', 'Comprehensive', 'Priority', 'Classic', 'Essential']
            },
            'momentum': {
                'name': 'Momentum Health',
                'code': 'MOM',
                'contact': '0860 11 78 78',
                'website': 'www.momentum.co.za',
                'plans': ['Ingwe', 'Leopard', 'Cheetah', 'Jaguar']
            },
            'bonitas': {
                'name': 'Bonitas Medical Fund',
                'code': 'BON',
                'contact': '0860 002 108',
                'website': 'www.bonitas.co.za',
                'plans': ['BonCap', 'BonEssential', 'BonFit', 'BonComprehensive']
            },
            'medshield': {
                'name': 'Medshield Medical Scheme',
                'code': 'MED',
                'contact': '0860 633 744',
                'website': 'www.medshield.co.za',
                'plans': ['MediCore', 'MediValue', 'MediElite']
            },
            'gems': {
                'name': 'Government Employees Medical Scheme',
                'code': 'GEMS',
                'contact': '0860 436 769',
                'website': 'www.gems.gov.za',
                'plans': ['Emerald', 'Sapphire', 'Ruby', 'Onyx']
            },
            'bestmed': {
                'name': 'Bestmed Medical Scheme',
                'code': 'BEST',
                'contact': '0860 002 378',
                'website': 'www.bestmed.co.za',
                'plans': ['Beat 1', 'Beat 2', 'Beat 3', 'Beat 4']
            }
        }
    
    def _load_provinces(self) -> Dict[str, Dict[str, Any]]:
        """Load South African provinces and major cities"""
        return {
            'GP': {
                'name': 'Gauteng',
                'capital': 'Johannesburg',
                'cities': ['Johannesburg', 'Pretoria', 'Soweto', 'Ekurhuleni', 'Vanderbijlpark'],
                'timezone': 'Africa/Johannesburg'
            },
            'WC': {
                'name': 'Western Cape',
                'capital': 'Cape Town',
                'cities': ['Cape Town', 'Stellenbosch', 'Paarl', 'George', 'Worcester'],
                'timezone': 'Africa/Johannesburg'
            },
            'KZN': {
                'name': 'KwaZulu-Natal',
                'capital': 'Pietermaritzburg',
                'cities': ['Durban', 'Pietermaritzburg', 'Newcastle', 'Richards Bay', 'Ladysmith'],
                'timezone': 'Africa/Johannesburg'
            },
            'EC': {
                'name': 'Eastern Cape',
                'capital': 'Bhisho',
                'cities': ['Port Elizabeth', 'East London', 'Uitenhage', 'King Williams Town', 'Grahamstown'],
                'timezone': 'Africa/Johannesburg'
            },
            'FS': {
                'name': 'Free State',
                'capital': 'Bloemfontein',
                'cities': ['Bloemfontein', 'Welkom', 'Kroonstad', 'Bethlehem', 'Sasolburg'],
                'timezone': 'Africa/Johannesburg'
            },
            'MP': {
                'name': 'Mpumalanga',
                'capital': 'Nelspruit',
                'cities': ['Nelspruit', 'Witbank', 'Middelburg', 'Secunda', 'Standerton'],
                'timezone': 'Africa/Johannesburg'
            },
            'LP': {
                'name': 'Limpopo',
                'capital': 'Polokwane',
                'cities': ['Polokwane', 'Tzaneen', 'Phalaborwa', 'Musina', 'Thohoyandou'],
                'timezone': 'Africa/Johannesburg'
            },
            'NW': {
                'name': 'North West',
                'capital': 'Mafikeng',
                'cities': ['Rustenburg', 'Mafikeng', 'Potchefstroom', 'Klerksdorp', 'Brits'],
                'timezone': 'Africa/Johannesburg'
            },
            'NC': {
                'name': 'Northern Cape',
                'capital': 'Kimberley',
                'cities': ['Kimberley', 'Upington', 'Kuruman', 'De Aar', 'Springbok'],
                'timezone': 'Africa/Johannesburg'
            }
        }
    
    def translate(self, key: str, language: str = None) -> str:
        """Translate a key to the specified language"""
        if language is None:
            language = self.default_language
        
        if language not in self.translations:
            language = self.default_language
        
        return self.translations[language].get(key, key)
    
    def format_date(self, date: datetime, language: str = None) -> str:
        """Format date in South African format (DD/MM/YYYY)"""
        return date.strftime('%d/%m/%Y')
    
    def format_time(self, time: datetime, language: str = None) -> str:
        """Format time in 24-hour format"""
        return time.strftime('%H:%M')
    
    def format_datetime(self, dt: datetime, language: str = None) -> str:
        """Format datetime in South African format"""
        return f"{self.format_date(dt, language)} {self.format_time(dt, language)}"
    
    def format_currency(self, amount: float, language: str = None) -> str:
        """Format currency in South African Rand"""
        return f"R {amount:,.2f}"
    
    def format_phone(self, phone: str) -> str:
        """Format phone number in South African format"""
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        
        # Handle different formats
        if digits.startswith('27'):
            # International format
            return f"+27 {digits[2:4]} {digits[4:7]} {digits[7:]}"
        elif digits.startswith('0'):
            # Local format
            return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
        else:
            return phone
    
    def validate_id_number(self, id_number: str) -> bool:
        """Validate South African ID number"""
        if not id_number or len(id_number) != 13:
            return False
        
        if not id_number.isdigit():
            return False
        
        # Luhn algorithm check
        total = 0
        for i, digit in enumerate(id_number[:-1]):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n = n // 10 + n % 10
            total += n
        
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(id_number[-1])
    
    def get_medical_aid_info(self, code: str) -> Optional[Dict[str, Any]]:
        """Get medical aid information by code"""
        for aid_id, aid_info in self.medical_aids.items():
            if aid_info['code'] == code.upper():
                return aid_info
        return None
    
    def get_province_info(self, code: str) -> Optional[Dict[str, Any]]:
        """Get province information by code"""
        return self.provinces.get(code.upper())
    
    def get_medical_term(self, category: str, code: str) -> str:
        """Get medical term by category and code"""
        return self.medical_terms.get(category, {}).get(code, code)
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
        return self.languages.copy()
    
    def detect_language_preference(self, user_agent: str = None, accept_language: str = None) -> str:
        """Detect user's language preference"""
        # Simple language detection based on Accept-Language header
        if accept_language:
            for lang_code in self.languages.keys():
                if lang_code in accept_language.lower():
                    return lang_code
        
        return self.default_language

# Global localization instance
sa_localization = SouthAfricanLocalization()
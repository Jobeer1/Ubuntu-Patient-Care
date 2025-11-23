"""Lightweight OCR for Document Processing"""
from typing import Optional, Dict, Any, List
import os

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("WARNING: pytesseract/PIL not installed. Install with: pip install pytesseract pillow")


class OCRService:
    """Service for Optical Character Recognition (offline-capable)"""
    
    @staticmethod
    def is_available() -> bool:
        """Check if OCR is available"""
        return OCR_AVAILABLE
    
    @staticmethod
    def extract_text_from_image(
        image_path: str,
        language: str = "eng"
    ) -> Dict[str, Any]:
        """
        Extract text from image using Tesseract OCR
        
        Args:
            image_path: Path to image file
            language: Language code (eng, afr, zul, xho, sot)
        
        Returns:
            {
                "success": True,
                "text": "Extracted text",
                "language": "eng",
                "confidence": 0.92
            }
        """
        if not OCR_AVAILABLE:
            return {
                "success": False,
                "error": "pytesseract not installed"
            }
        
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image not found: {image_path}"
            }
        
        try:
            image = Image.open(image_path)
            
            # Extract text
            text = pytesseract.image_to_string(image, lang=language)
            
            # Get detailed data for confidence
            data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "success": True,
                "text": text.strip(),
                "language": language,
                "confidence": avg_confidence / 100.0,  # Convert to 0-1 scale
                "character_count": len(text),
                "word_count": len(text.split())
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def extract_form_fields(
        image_path: str,
        form_type: str = "preauth"
    ) -> Dict[str, Any]:
        """
        Extract structured data from medical forms
        
        Args:
            image_path: Path to form image
            form_type: Type of form (preauth, patient_info, insurance)
        
        Returns:
            Extracted form fields with structure
        """
        if not OCR_AVAILABLE:
            return {
                "success": False,
                "error": "pytesseract not installed"
            }
        
        # First extract all text
        result = OCRService.extract_text_from_image(image_path)
        if not result.get("success"):
            return result
        
        text = result.get("text", "")
        
        # Parse based on form type
        if form_type == "preauth":
            fields = _parse_preauth_form(text)
        elif form_type == "patient_info":
            fields = _parse_patient_info_form(text)
        elif form_type == "insurance":
            fields = _parse_insurance_form(text)
        else:
            fields = _parse_generic_form(text)
        
        return {
            "success": True,
            "form_type": form_type,
            "extracted_fields": fields,
            "raw_text": text,
            "confidence": result.get("confidence")
        }
    
    @staticmethod
    def extract_medical_id(
        id_image_path: str,
        id_type: str = "sa_id"
    ) -> Dict[str, Any]:
        """
        Extract information from medical ID document
        
        Args:
            id_image_path: Path to ID image
            id_type: Type of ID (sa_id, passport, medical_aid_card)
        
        Returns:
            Extracted ID information
        """
        if not OCR_AVAILABLE:
            return {
                "success": False,
                "error": "pytesseract not installed"
            }
        
        result = OCRService.extract_text_from_image(id_image_path)
        if not result.get("success"):
            return result
        
        text = result.get("text", "")
        
        if id_type == "sa_id":
            extracted = _parse_sa_id(text)
        elif id_type == "medical_aid_card":
            extracted = _parse_medical_aid_card(text)
        elif id_type == "passport":
            extracted = _parse_passport(text)
        else:
            extracted = _parse_generic_id(text)
        
        return {
            "success": True,
            "id_type": id_type,
            "extracted_data": extracted,
            "raw_text": text,
            "confidence": result.get("confidence")
        }
    
    @staticmethod
    def extract_handwritten_text(
        image_path: str
    ) -> Dict[str, Any]:
        """
        Extract handwritten text from image
        
        (Tesseract can handle handwriting but with lower accuracy)
        """
        result = OCRService.extract_text_from_image(image_path, language="eng")
        
        if result.get("success"):
            result["note"] = "Handwriting recognition may have lower accuracy"
        
        return result
    
    @staticmethod
    def list_supported_languages() -> Dict[str, str]:
        """List supported languages for OCR"""
        return {
            "eng": "English",
            "afr": "Afrikaans",
            "zul": "Zulu",
            "xho": "Xhosa",
            "sot": "Sotho",
            "ssw": "Swati",
            "tsn": "Tswana",
            "tso": "Tsonga",
            "ven": "Venda",
            "nde": "Ndebele"
        }


def _parse_preauth_form(text: str) -> Dict[str, Any]:
    """Parse pre-authorization form fields"""
    import re
    
    fields = {
        "patient_name": _extract_field(text, r"patient\s*name[\s:]*(\w+\s+\w+)", 0),
        "patient_id": _extract_field(text, r"patient\s*id[\s:]*(\w+)", 0),
        "member_number": _extract_field(text, r"member\s*number[\s:]*(\d+)", 0),
        "date_of_birth": _extract_field(text, r"date\s*of\s*birth[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", 0),
        "procedure": _extract_field(text, r"procedure[\s:]*([^\n]+)", 0),
        "clinical_indication": _extract_field(text, r"indication[\s:]*([^\n]+)", 0),
        "urgency": _extract_urgency_level(text),
        "doctor_name": _extract_field(text, r"doctor[\s:]*(\w+\s+\w+)", 0),
        "clinic_name": _extract_field(text, r"clinic[\s:]*([^\n]+)", 0)
    }
    
    return {k: v for k, v in fields.items() if v}


def _parse_patient_info_form(text: str) -> Dict[str, Any]:
    """Parse patient information form"""
    fields = {
        "full_name": _extract_field(text, r"name[\s:]*(\w+\s+\w+)", 0),
        "date_of_birth": _extract_field(text, r"birth[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", 0),
        "id_number": _extract_field(text, r"(?:id|identification)[\s:]*(\d+)", 0),
        "phone": _extract_field(text, r"phone[\s:]*(\d{10,})", 0),
        "email": _extract_field(text, r"email[\s:]*(\S+@\S+)", 0),
        "address": _extract_field(text, r"address[\s:]*([^\n]+)", 0),
        "emergency_contact": _extract_field(text, r"emergency[\s:]*(\w+\s+\w+)", 0)
    }
    
    return {k: v for k, v in fields.items() if v}


def _parse_insurance_form(text: str) -> Dict[str, Any]:
    """Parse insurance/medical aid form"""
    fields = {
        "scheme_name": _extract_field(text, r"scheme[\s:]*(\w+(?:\s+\w+)?)", 0),
        "member_number": _extract_field(text, r"member[\s:]*(\d+)", 0),
        "plan_name": _extract_field(text, r"plan[\s:]*([^\n]+)", 0),
        "coverage_type": _extract_field(text, r"coverage[\s:]*(\w+)", 0),
        "effective_date": _extract_field(text, r"effective[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", 0),
        "expiry_date": _extract_field(text, r"expir(?:y|ation)[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", 0)
    }
    
    return {k: v for k, v in fields.items() if v}


def _parse_generic_form(text: str) -> Dict[str, Any]:
    """Parse generic form - extract key-value pairs"""
    import re
    
    fields = {}
    # Look for patterns like "Label: Value"
    matches = re.findall(r"(\w+(?:\s+\w+)?)\s*[:=]\s*([^\n]+)", text)
    
    for label, value in matches:
        if len(label) > 2 and len(value) > 2:  # Filter noise
            fields[label.lower().replace(" ", "_")] = value.strip()
    
    return fields


def _parse_sa_id(text: str) -> Dict[str, Any]:
    """Extract data from South African ID"""
    import re
    
    # South African ID format: YYMMDDSSSSCCAZ
    id_match = re.search(r'\b\d{13}[A-Z]\b', text)
    
    data = {}
    if id_match:
        id_num = id_match.group(0)
        # Parse components
        year = id_num[0:2]
        month = id_num[2:4]
        day = id_num[4:6]
        data["id_number"] = id_num
        data["date_of_birth"] = f"19{year}-{month}-{day}"
        
        sequence = id_num[6:10]
        gender_code = id_num[10]
        data["gender"] = "Female" if int(gender_code) < 5 else "Male"
    
    data["name"] = _extract_field(text, r"name[\s:]*(\w+\s+\w+)", 0)
    data["surname"] = _extract_field(text, r"surname[\s:]*(\w+)", 0)
    
    return data


def _parse_medical_aid_card(text: str) -> Dict[str, Any]:
    """Extract data from medical aid card"""
    data = {
        "scheme_name": _extract_field(text, r"(?:scheme|medical\s+aid)[\s:]*(\w+)", 0),
        "member_number": _extract_field(text, r"member[\s:]*(\d+)", 0),
        "member_name": _extract_field(text, r"name[\s:]*(\w+\s+\w+)", 0),
        "plan_name": _extract_field(text, r"plan[\s:]*(\w+(?:\s+\w+)?)", 0),
        "validity": _extract_field(text, r"valid[\s:]*([^\n]+)", 0)
    }
    
    return {k: v for k, v in data.items() if v}


def _parse_passport(text: str) -> Dict[str, Any]:
    """Extract data from passport"""
    data = {
        "surname": _extract_field(text, r"surname[\s:]*(\w+)", 0),
        "given_names": _extract_field(text, r"given\s+names[\s:]*(\w+\s+\w+)", 0),
        "passport_number": _extract_field(text, r"number[\s:]*(\w+)", 0),
        "nationality": _extract_field(text, r"nationality[\s:]*(\w+)", 0),
        "date_of_birth": _extract_field(text, r"birth[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", 0),
        "issue_date": _extract_field(text, r"issue[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", 0),
        "expiry_date": _extract_field(text, r"expir(?:y|ation)[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", 0)
    }
    
    return {k: v for k, v in data.items() if v}


def _parse_generic_id(text: str) -> Dict[str, Any]:
    """Extract generic ID information"""
    data = {
        "id_number": _extract_field(text, r"(?:id|number)[\s:]*(\d+)", 0),
        "name": _extract_field(text, r"name[\s:]*(\w+\s+\w+)", 0),
        "date_of_birth": _extract_field(text, r"birth[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", 0),
        "expiry_date": _extract_field(text, r"expir(?:y|ation)[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", 0)
    }
    
    return {k: v for k, v in data.items() if v}


def _extract_field(text: str, pattern: str, group: int) -> Optional[str]:
    """Helper to extract field using regex"""
    import re
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(group).strip() if match else None


def _extract_urgency_level(text: str) -> str:
    """Extract urgency level"""
    text_lower = text.lower()
    if any(word in text_lower for word in ["emergency", "urgent", "asap", "critical"]):
        return "emergency"
    elif any(word in text_lower for word in ["urgent", "soon"]):
        return "urgent"
    return "routine"

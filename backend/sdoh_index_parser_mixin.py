from __future__ import annotations

"""SDOH Patient Index — DICOM, PDF, and Text Parsing Mixin
==========================================================
Mixin providing all file-parsing methods for PatientDocumentIndexer.
Inheriting this mixin keeps the main indexer class focused on scanning,
searching, and exporting.

Patient-sovereignty note: parsing reads local files only — no content
leaves the device.
"""

import re
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.sdoh_index_vocab import (
    BODY_PART_KEYWORDS,
    CLINICAL_PLAIN_LANGUAGE,
    DICOM_TAG_MAP,
    MODALITY_LABELS,
)


class PatientIndexParserMixin:

    # ------------------------------------------------------------------
    # DICOM parsing
    # ------------------------------------------------------------------

    def _parse_dicom(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a DICOM file, returning metadata entry. Falls back to raw-byte sniff.
        
        Runs pydicom.dcmread inside a thread with an 8-second hard timeout
        to prevent hangs when network shares stall during os.stat().
        """
        import threading

        _result = [None]
        _done = threading.Event()

        def _read():
            try:
                import pydicom
                import warnings
                warnings.filterwarnings('ignore', category=UserWarning, module='pydicom')
                try:
                    ds = pydicom.dcmread(file_path, stop_before_pixels=True, force=True)
                except Exception as e:
                    print(f'[SDOH] pydicom read failed for {file_path}: {e}, using fallback')
                    _result[0] = self._parse_dicom_fallback(file_path)
                    _done.set()
                    return

                entry: Dict[str, Any] = {
                    "file_path": file_path,
                    "file_type": "dicom",
                    "indexed_at": datetime.utcnow().isoformat(),
                }

                for tag_name, field in DICOM_TAG_MAP.items():
                    try:
                        value = getattr(ds, tag_name, None)
                        if value is not None:
                            entry[field] = str(value).strip()
                    except Exception:
                        pass

                try:
                    if hasattr(ds, 'PatientAge') and ds.PatientAge:
                        entry['patient_age'] = str(ds.PatientAge).strip()
                    if hasattr(ds, 'PatientSex') and ds.PatientSex:
                        entry['patient_sex'] = str(ds.PatientSex).strip()
                    if hasattr(ds, 'StudyTime') and ds.StudyTime:
                        entry['study_time'] = str(ds.StudyTime).strip()
                    if hasattr(ds, 'SeriesTime') and ds.SeriesTime:
                        entry['series_time'] = str(ds.SeriesTime).strip()
                    if hasattr(ds, 'Manufacturer') and ds.Manufacturer:
                        entry['manufacturer'] = str(ds.Manufacturer).strip()
                    if hasattr(ds, 'ManufacturerModelName') and ds.ManufacturerModelName:
                        entry['equipment_model'] = str(ds.ManufacturerModelName).strip()
                    if hasattr(ds, 'NumberOfFrames') and ds.NumberOfFrames:
                        entry['number_of_frames'] = str(ds.NumberOfFrames).strip()
                    if hasattr(ds, 'Rows') and ds.Rows:
                        entry['image_height'] = int(ds.Rows)
                    if hasattr(ds, 'Columns') and ds.Columns:
                        entry['image_width'] = int(ds.Columns)
                except Exception:
                    pass

                # Format study date for display
                raw_date = entry.get("study_date", "")
                if re.match(r"^\d{8}$", raw_date):
                    entry["study_date_display"] = (
                        f"{raw_date[6:8]}/{raw_date[4:6]}/{raw_date[0:4]}"
                    )

                # Get modality label
                raw_mod = entry.get("modality", "").upper()
                entry["modality_label"] = MODALITY_LABELS.get(raw_mod, raw_mod)

                # Infer body part from study and series descriptions
                body_hint = (
                    (entry.get("body_part", "") or "")
                    + " "
                    + (entry.get("study_description", "") or "")
                    + " "
                    + (entry.get("series_description", "") or "")
                )
                entry["body_part_normalized"] = self._normalize_body_part(body_hint)

                entry["summary"] = self._dicom_summary(entry)
                entry["relevance_keywords"] = self._keywords_from_dicom(entry)

                _result[0] = entry
                _done.set()
            except Exception as e:
                print(f'[SDOH] _parse_dicom thread error for {file_path}: {e}')
                _done.set()

        _t = threading.Thread(target=_read, daemon=True)
        _t.start()
        _t.join(timeout=8)  # hard timeout — network drives can stall os.stat

        if _done.is_set():
            return _result[0] if _result[0] is not None else self._parse_dicom_fallback(file_path)

        # Timeout reached — pydicom.dcmread/os.stat hung on network drive
        print(f'[SDOH] _parse_dicom timed out for {file_path}, using fallback')
        return self._parse_dicom_fallback(file_path)

    def _is_dicom_file(self, file_path: str) -> bool:
        """
        Check if a file is a DICOM file by reading magic bytes.
        
        DICOM files start with:
        - 128 bytes of preamble (zeros or arbitrary)
        - Then 'DICM' at offset 128
        
        This allows detection of DICOM files without .dcm extension.
        """
        try:
            with open(file_path, "rb") as fh:
                # Check for DICM signature at offset 128
                fh.seek(128)
                signature = fh.read(4)
                return signature == b'DICM'
        except Exception:
            return False

    def _parse_dicom_fallback(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract basic metadata from a DICOM file without pydicom by reading raw bytes.
        
        This is a fallback for when pydicom is not installed. It extracts:
        - Patient ID, name, and demographics from tag VR blocks
        - Study description and series description
        - Modality from file tags
        - Study date and time
        """
        try:
            with open(file_path, "rb") as fh:
                # Read first 8KB for DICOM tags (most headers are in first 4KB)
                raw = fh.read(8192)
            
            entry: Dict[str, Any] = {
                "file_path": file_path,
                "file_type": "dicom",
                "indexed_at": datetime.utcnow().isoformat(),
                "summary": "DICOM medical imaging study",
                "relevance_keywords": ["dicom", "medical image"],
            }
            
            # Extract any readable ASCII strings of 4+ chars
            text_parts = []
            current_str = []
            for b in raw:
                if 32 <= b <= 126:  # Printable ASCII
                    current_str.append(chr(b))
                else:
                    if len(current_str) >= 4:
                        candidate = "".join(current_str).strip()
                        if len(candidate) > 2 and not candidate.startswith(chr(0)):
                            text_parts.append(candidate)
                    current_str = []
            
            text_lower = " ".join(text_parts).lower()
            
            # Try to identify modality
            for mod_code, mod_label in MODALITY_LABELS.items():
                if mod_code.lower() in text_lower or mod_label.lower() in text_lower:
                    entry["modality"] = mod_code
                    entry["modality_label"] = mod_label
                    break
            
            # If no modality found, check for common abbreviations
            if "modality" not in entry:
                for term, (mod_code, mod_label) in [
                    ("x-ray", ("CR", "X-Ray")),
                    ("xray", ("CR", "X-Ray")),
                    ("ultrasound", ("US", "Ultrasound")),
                    ("computed tomography", ("CT", "CT Scan")),
                    ("ct scan", ("CT", "CT Scan")),
                    ("mri", ("MR", "MRI")),
                    ("magnetic resonance", ("MR", "MRI")),
                    ("mammogr", ("MG", "Mammography")),
                    ("pet", ("PT", "PET Scan")),
                    ("nuclear", ("NM", "Nuclear Medicine")),
                ]:
                    if term in text_lower:
                        entry["modality"] = mod_code
                        entry["modality_label"] = mod_label
                        break
            
            entry["body_part_normalized"] = self._normalize_body_part(" ".join(text_parts))
            
            if entry.get("modality_label"):
                parts = [entry["modality_label"]]
                if entry.get("body_part_normalized"):
                    parts.append(f"of {entry['body_part_normalized']}")
                entry["summary"] = " ".join(parts) + " (metadata fallback)"
            
            return entry
        except Exception:
            return None

    # ------------------------------------------------------------------
    # PDF / text parsing
    # ------------------------------------------------------------------

    def _parse_pdf(self, file_path: str) -> Optional[Dict[str, Any]]:
        text = ""
        try:
            import pdfminer.high_level  # type: ignore
            text = pdfminer.high_level.extract_text(file_path) or ""
        except (ImportError, Exception):
            pass

        if not text:
            try:
                import pypdf  # type: ignore
                reader = pypdf.PdfReader(file_path)
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                pass

        if not text:
            return {
                "file_path": file_path,
                "file_type": "pdf",
                "indexed_at": datetime.utcnow().isoformat(),
                "summary": "PDF medical document (text extraction unavailable — install pdfminer.six)",
                "document_type": "pdf",
                "relevance_keywords": ["document", "pdf"],
            }

        return self._build_text_entry(file_path, "pdf", text)

    def _parse_openclaw_session(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            import json
            messages = []
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip(): continue
                    try:
                        d = json.loads(line)
                        role = "unknown"
                        text_content = ""
                        
                        if d.get("type") == "message" and "message" in d:
                            msg = d["message"]
                            role = msg.get("role", "unknown")
                            content = msg.get("content", "")
                        else:
                            role = d.get("role", "")
                            content = d.get("content", "")

                        if not role or role == "unknown":
                            continue

                        if isinstance(content, list):
                            for block in content:
                                b_type = block.get("type", "")
                                if b_type == "text":
                                    text_content += block.get("text", "") + " "
                                elif b_type == "image" or "image_url" in block:
                                    text_content += "[Picture/Image Attached] "
                                elif b_type == "audio" or "audio_url" in block:
                                    text_content += "[Voice Note Attached] "
                                else:
                                    text_content += str(block) + " "
                        else:
                            text_content = str(content)
                        
                        text_content = text_content.strip()
                        if not text_content: continue
                        if "[OpenClaw heartbeat poll]" in text_content or "[assistant turn failed" in text_content:
                            continue
                            
                        messages.append(f"{role.upper()}: {text_content}")
                    except Exception:
                        pass
            
            if not messages:
                return self._parse_text(file_path)
            
            full_text = "\n".join(messages)
            entry = self._build_text_entry(file_path, "whatsapp_session", full_text)
            entry["summary"] = f"WhatsApp Session Transcript ({len(messages)} messages)"
            entry["relevance_keywords"] = list(set(entry.get("relevance_keywords", []) + ["whatsapp", "chat", "conversation", "message", "voice note", "picture"]))
            return entry
        except Exception:
            return None

    def _parse_text(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            return self._build_text_entry(file_path, "text", text)
        except Exception:
            return None

    def _parse_firebird(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            import os
            from datetime import datetime
            import string
            
            stat = os.stat(file_path)
            
            extracted_text = ""
            try:
                with open(file_path, 'rb') as f:
                    start_offset = min(10 * 1024 * 1024, max(0, stat.st_size - 5 * 1024 * 1024))
                    f.seek(start_offset)
                    data = f.read(5 * 1024 * 1024)
                    
                    current_str = []
                    for b in data:
                        if 32 <= b <= 126:
                            current_str.append(chr(b))
                        else:
                            if len(current_str) >= 6:
                                candidate = "".join(current_str)
                                if not candidate.startswith('UUUU') and not candidate.startswith('    '):
                                    extracted_text += candidate + " "
                            current_str = []
            except Exception as read_e:
                extracted_text = f"[Binary read error: {read_e}]"
                
            preview = extracted_text[:800].strip() if extracted_text else "[Firebird Database - No readable text in surveyed blocks]"
            
            entry = {
                "file_path": file_path,
                "file_type": "firebird_database",
                "indexed_at": datetime.utcnow().isoformat(),
                "text_preview": f"Size: {stat.st_size} bytes. Context Snippet: {preview}",
                "study_date_display": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d'),
            }
            return entry
        except Exception:
            return None

    def _build_text_entry(self, file_path: str, file_type: str, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        entry: Dict[str, Any] = {
            "file_path": file_path,
            "file_type": file_type,
            "indexed_at": datetime.utcnow().isoformat(),
            "text_preview": text[:400].strip(),
        }

        date_match = re.search(
            r"\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2})\b", text
        )
        if date_match:
            entry["study_date_display"] = date_match.group(0)

        for mod_code, mod_label in MODALITY_LABELS.items():
            if mod_code.lower() in text_lower or mod_label.lower() in text_lower:
                entry["modality"] = mod_code
                entry["modality_label"] = mod_label
                break
        if "modality" not in entry:
            for term, mod in [
                ("x-ray", "CR"), ("xray", "CR"), ("ultrasound", "US"),
                ("computed tomography", "CT"), ("magnetic resonance", "MR"),
                ("pet scan", "PT"), ("nuclear medicine", "NM"),
                ("mammograph", "MG"), ("fluoroscop", "RF"),
            ]:
                if term in text_lower:
                    entry["modality"] = mod
                    entry["modality_label"] = MODALITY_LABELS.get(mod, mod)
                    break

        entry["body_part_normalized"] = self._normalize_body_part(text)

        doc_type = "report"
        if any(w in text_lower for w in ["prescribed", "dispense", "tablet", "capsule", " mg ", "dosage", "medication", "script", "prescription"]):
            doc_type = "script"
        elif any(w in text_lower for w in ["referred", "referral", "please see", "please assess", "kindly see", "review this patient", "for specialist"]):
            doc_type = "referral"
        elif any(w in text_lower for w in ["discharge", "admitted", "ward", "theatre", "surgery", "post-operative", "operation"]):
            doc_type = "discharge_summary"
        elif any(w in text_lower for w in ["haemoglobin", "haematocrit", "wbc", "rbc", "platelet", "creatinine", "sodium", "potassium", "glucose", "cholesterol", "urea", "albumin", "bilirubin", "alt ", "ast ", "ggt"]):
            doc_type = "lab_results"
        entry["document_type"] = doc_type

        found_terms = [term for term in CLINICAL_PLAIN_LANGUAGE if term in text_lower]
        entry["clinical_terms"] = found_terms[:10]

        entry["summary"] = self._text_summary(entry)
        entry["relevance_keywords"] = self._keywords_from_text(entry, text)
        return entry

    # ------------------------------------------------------------------
    # Normalisation and summary helpers
    # ------------------------------------------------------------------

    def _normalize_body_part(self, text: str) -> Optional[str]:
        text_lower = (text or "").lower()
        for part, terms in BODY_PART_KEYWORDS.items():
            if any(t in text_lower for t in terms):
                return part
        return None

    def _dicom_summary(self, entry: Dict[str, Any]) -> str:
        parts = []
        if entry.get("modality_label"):
            parts.append(entry["modality_label"])
        if entry.get("body_part_normalized"):
            parts.append(f"of the {entry['body_part_normalized']}")
        elif entry.get("body_part"):
            parts.append(f"({entry['body_part']})")
        if entry.get("study_date_display"):
            parts.append(f"dated {entry['study_date_display']}")
        if entry.get("institution"):
            parts.append(f"from {entry['institution']}")
        return " ".join(parts) if parts else "DICOM medical imaging study"

    def _text_summary(self, entry: Dict[str, Any]) -> str:
        label_map = {
            "script": "Medication script",
            "referral": "Referral letter",
            "discharge_summary": "Discharge summary",
            "lab_results": "Laboratory results",
            "report": "Medical report",
        }
        label = label_map.get(entry.get("document_type", ""), "Medical document")
        parts = [label]
        if entry.get("modality_label"):
            parts.append(f"— {entry['modality_label']}")
        if entry.get("body_part_normalized"):
            parts.append(f"({entry['body_part_normalized']})")
        if entry.get("study_date_display"):
            parts.append(f"dated {entry['study_date_display']}")
        return " ".join(parts)

    def _keywords_from_dicom(self, entry: Dict[str, Any]) -> List[str]:
        kw = []
        for field in ["modality", "body_part", "study_description", "series_description"]:
            v = (entry.get(field) or "").lower().strip()
            if v:
                kw.extend(v.split())
        return list(set(kw))

    def _keywords_from_text(self, entry: Dict[str, Any], text: str) -> List[str]:
        kw = list(entry.get("clinical_terms") or [])
        if entry.get("body_part_normalized"):
            kw.append(entry["body_part_normalized"])
        if entry.get("modality"):
            kw.append(entry["modality"].lower())
        if entry.get("document_type"):
            kw.append(entry["document_type"])
        return list(set(kw))

    # ------------------------------------------------------------------
    # Entry classification helpers
    # ------------------------------------------------------------------

    def _classify_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Classify a flat DICOM/JP2 entry for richer search and grouping."""
        # Document type
        modality = (entry.get("modality") or "").upper()
        if modality in {"CR", "DX", "MG", "RF", "XA", "XC"}:
            entry["document_type"] = "imaging"
        elif modality in {"CT", "MR", "PT", "NM", "US"}:
            entry["document_type"] = "imaging"
        else:
            entry["document_type"] = entry.get("document_type", "imaging")
        return entry

    def _build_medical_summary(self, entry: Dict[str, Any]) -> str:
        parts = []
        modality = entry.get("modality_label") or entry.get("modality", "")
        if modality:
            parts.append(str(modality))
        description = entry.get("study_description") or ""
        if description:
            parts.append(str(description))
        date = entry.get("study_date_display") or ""
        if date:
            parts.append(f"({date})")
        if not parts:
            return "Medical imaging study"
        return " ".join(parts)

    def _extract_body_part(self, entry: Dict[str, Any]) -> Optional[str]:
        for field in ("study_description", "series_description", "body_part"):
            text = entry.get(field) or ""
            for part, terms in BODY_PART_KEYWORDS.items():
                if any(t in text.lower() for t in terms):
                    return part
        return None

    def _extract_clinical_terms(self, entry: Dict[str, Any]) -> List[str]:
        text = (
            (entry.get("study_description") or "") + " " +
            (entry.get("series_description") or "") + " " +
            (entry.get("body_part") or "")
        ).lower()
        return sorted(set(t for t in CLINICAL_PLAIN_LANGUAGE if t in text))

    def _build_relevance_keywords(self, entry: Dict[str, Any]) -> List[str]:
        kw = []
        for field in ("modality", "modality_label", "body_part", "body_part_normalized",
                       "study_description", "series_description", "institution",
                       "referring_physician", "patient_name", "patient_id"):
            v = (entry.get(field) or "").strip()
            if v:
                kw.append(v.lower())
        return list(set(kw))

    # ------------------------------------------------------------------
    # JP2 parsing
    # ------------------------------------------------------------------

    def _parse_jp2(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse a JPEG2000 (JP2) file and extract metadata.
        
        JP2 files often accompany DICOM files. This parser:
        1. First tries to find and parse a companion DICOM file
        2. Falls back to direct JP2 header parsing for image metadata
        3. Infers study date from filesystem if possible
        
        Returns metadata entry with file_path pointing to JP2, not DICOM.
        """
        from datetime import datetime

        try:
            base_name = os.path.basename(file_path)
            # Handle various JP2 naming patterns: file.jp2, file.j2k, file.rst.jp2, etc.
            for ext in ['.rst.jp2', '.rst.j2k', '.jp2', '.j2k']:
                if base_name.lower().endswith(ext):
                    base_name = base_name[:-len(ext)]
                    break

            dir_name = os.path.dirname(file_path)

            # Search for companion DICOM in standard locations
            potential_dicom_paths = [
                os.path.join(dir_name, 'DICOM', base_name + '.dcm'),
                os.path.join(dir_name, base_name + '.dcm'),
                os.path.join(dir_name, '..', 'DICOM', base_name + '.dcm'),
                os.path.join(dir_name, 'dcm', base_name + '.dcm'),
            ]

            # Try each potential DICOM path
            for dcm_path in potential_dicom_paths:
                if os.path.exists(dcm_path):
                    entry = self._parse_dicom(dcm_path)
                    if entry:
                        # Preserve JP2 file path but use DICOM metadata
                        entry['file_path'] = file_path
                        entry['file_type'] = 'image'
                        entry['original_dicom'] = dcm_path
                        if entry.get('summary'):
                            entry['summary'] = entry['summary'].replace('DICOM', 'JPEG2000 (DICOM-sourced)')
                        else:
                            entry['summary'] = 'JPEG2000 medical image (DICOM-sourced)'

                        # Add JP2-specific keywords
                        if 'relevance_keywords' not in entry:
                            entry['relevance_keywords'] = []
                        entry['relevance_keywords'].extend(['image', 'jpeg2000', 'jp2', 'lossless', 'reversible'])
                        return entry

            # If no DICOM found, parse JP2 header directly
            entry = self._parse_jp2_header(file_path)
            if entry:
                return entry

            # Final fallback: minimal entry with filesystem info
            stat = os.stat(file_path)
            return {
                'file_path': file_path,
                'file_type': 'image',
                'indexed_at': datetime.utcnow().isoformat(),
                'study_date_display': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d'),
                'summary': 'JPEG2000 medical image',
                'relevance_keywords': ['image', 'jpeg2000', 'jp2', 'scan', 'medical image'],
            }
        except Exception as e:
            import sys
            print(f'[SDOH] JP2 parse error for {file_path}: {e}', file=sys.stderr)
            return {
                'file_path': file_path,
                'file_type': 'image',
                'indexed_at': datetime.utcnow().isoformat(),
                'summary': 'JPEG2000 medical image (parse error)',
                'relevance_keywords': ['image', 'jpeg2000', 'jp2'],
            }

    def _find_and_parse_companion_dicom(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Find and parse a companion DICOM file for the given file path.
        
        This method searches for DICOM files that companion the given file
        (e.g., for JP2 or JPG files) and returns parsed metadata if found.
        
        Args:
            file_path: Path to the file for which to find a companion DICOM
            
        Returns:
            Parsed DICOM metadata entry if companion found and parsed successfully,
            None otherwise
        """
        import os
        from datetime import datetime
        
        try:
            base_name = os.path.basename(file_path)
            # Handle various file naming patterns: file.rst.jp2, file.j2k, file.jpg, etc.
            # Remove known extensions to get the base name
            for ext in ['.rst.jp2', '.rst.j2k', '.jp2', '.j2k', '.jpg', '.jpeg', '.png']:
                if base_name.lower().endswith(ext):
                    base_name = base_name[:-len(ext)]
                    break

            dir_name = os.path.dirname(file_path)

            # Search for companion DICOM in standard locations
            potential_dicom_paths = [
                os.path.join(dir_name, 'DICOM', base_name + '.dcm'),
                os.path.join(dir_name, base_name + '.dcm'),
                os.path.join(dir_name, '..', 'DICOM', base_name + '.dcm'),
                os.path.join(dir_name, 'dcm', base_name + '.dcm'),
            ]

            # Try each potential DICOM path
            for dcm_path in potential_dicom_paths:
                if os.path.exists(dcm_path):
                    entry = self._parse_dicom(dcm_path)
                    if entry:
                        return entry
                        
            # No companion DICOM found
            return None
        except Exception as e:
            import sys
            print(f'[SDOH] Companion DICOM parse error for {file_path}: {e}', file=sys.stderr)
            return None

    def _parse_jp2_header(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract basic metadata from JP2 file header without external library.
        """
        from datetime import datetime
        import struct
        import os

        try:
            with open(file_path, 'rb') as f:
                # JP2 signature: 00 00 00 0C 6A 50 20 20 0D 0A 87 0A
                header = f.read(12)
                if header[:4] != b'\x00\x00\x00\x0c' or header[4:8] != b'jP  ':
                    return None

                entry = {
                    'file_path': file_path,
                    'file_type': 'image',
                    'indexed_at': datetime.utcnow().isoformat(),
                    'modality': 'OT',  # Other
                    'modality_label': 'Optical/JPEG2000 Image',
                    'summary': 'JPEG2000 medical image',
                    'relevance_keywords': ['image', 'jpeg2000', 'jp2', 'scan'],
                }

                f.seek(0)
                data = f.read(65536)

                i = 12
                while i < len(data) - 8:
                    box_len_bytes = data[i:i+4]
                    box_type = data[i+4:i+8]

                    if len(box_len_bytes) < 4:
                        break

                    box_len = struct.unpack('>I', box_len_bytes)[0]
                    if box_len == 0:
                        box_len = len(data) - i
                    if box_len < 8 or box_len > 1000000:
                        i += 8
                        continue

                    if box_type == b'ihdr':
                        if i + 14 < len(data):
                            height, width = struct.unpack('>II', data[i+8:i+16])
                            entry['image_height'] = height
                            entry['image_width'] = width
                            entry['summary'] = f"JPEG2000 image ({width}x{height}px)"

                    elif box_type == b'colr':
                        if i + 11 < len(data):
                            colr_data = data[i+8:min(i+box_len, len(data))]
                            if len(colr_data) >= 3:
                                cs = struct.unpack('>I', b'\x00' + colr_data[1:4])[0]
                                cs_names = {
                                    0: 'sRGB', 1: 'Greyscale', 2: 'sYCC', 3: 'esRGB',
                                    4: 'ROMMRGB', 5: 'Profiled', 6: 'Enumerated'
                                }
                                entry['colorspace'] = cs_names.get(cs, f'CS{cs}')

                    elif box_type == b'xml ' or box_type == b'uuid':
                        metadata_chunk = data[i+8:min(i+box_len, i+512)]
                        if b'dicom' in metadata_chunk.lower() or b'medical' in metadata_chunk.lower():
                            entry['has_metadata'] = True

                    i += box_len

                stat = os.stat(file_path)
                entry['study_date_display'] = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')

                return entry
        except Exception:
            return None
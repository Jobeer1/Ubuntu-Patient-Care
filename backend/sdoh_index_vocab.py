"""SDOH Patient Index — Clinical Vocabulary
==========================================
Module-level vocabulary dictionaries used by the patient document indexer
and the SDOH agent.  No classes — import the dicts directly.

Patient-sovereignty note: these dictionaries never leave the device.
"""
from __future__ import annotations

from typing import Dict, List

MODALITY_LABELS: Dict[str, str] = {
    "CT": "CT Scan",
    "MR": "MRI",
    "CR": "X-Ray",
    "DX": "Digital X-Ray",
    "US": "Ultrasound",
    "PT": "PET Scan",
    "NM": "Nuclear Medicine Scan",
    "MG": "Mammogram",
    "RF": "Fluoroscopy",
    "XA": "Angiography",
    "SR": "Structured Report",
    "ECG": "ECG",
    "OT": "Other",
}

BODY_PART_KEYWORDS: Dict[str, List[str]] = {
    "chest": ["chest", "thorax", "thoracic", "lung", "lungs", "pulmonary", "heart", "cardiac", "mediastin", "pleura"],
    "abdomen": ["abdomen", "abdominal", "liver", "kidney", "renal", "bowel", "colon", "spleen", "pancreas", "gallbladder", "hepatic"],
    "brain": ["brain", "head", "neuro", "cerebral", "cranial", "skull", "intracranial", "cerebellum", "cortex"],
    "spine": ["spine", "vertebra", "vertebral", "cervical spine", "lumbar", "thoracic spine", "sacral", "spinal cord", "disc", "disk"],
    "pelvis": ["pelvis", "pelvic", "hip", "bladder", "prostate", "ovary", "uterus", "endometrium", "rectum"],
    "breast": ["breast", "mammogram", "mammography", "axilla"],
    "neck": ["neck", "thyroid", "cervical", "parathyroid", "carotid"],
    "extremity": ["arm", "leg", "knee", "shoulder", "elbow", "wrist", "ankle", "foot", "hand", "femur", "tibia", "fibula", "humerus"],
}

CLINICAL_PLAIN_LANGUAGE: Dict[str, str] = {
    "lesion": "an area that looks different from normal tissue and needs monitoring",
    "nodule": "a small lump or growth that may need follow-up",
    "mass": "a growth larger than a nodule — the doctor will want to investigate further",
    "opacity": "an area that appears lighter than expected on the scan, sometimes caused by fluid or infection",
    "effusion": "fluid that has built up where it should not be",
    "calcification": "calcium deposits — these can be completely normal or may need monitoring depending on where they are",
    "pneumonia": "a lung infection that causes part of the lung to look cloudy or filled with fluid",
    "atelectasis": "a small area of the lung that has partially collapsed — often temporary",
    "cardiomegaly": "the heart appears larger than normal on the image",
    "hepatomegaly": "the liver appears larger than normal",
    "splenomegaly": "the spleen appears larger than normal",
    "bilateral": "affecting both sides of the body",
    "unilateral": "affecting only one side of the body",
    "acute": "this is happening suddenly or has started recently",
    "chronic": "this is an ongoing or long-standing condition",
    "benign": "not cancerous — no immediate danger",
    "malignant": "cancerous or suspected to be cancerous — requires urgent follow-up",
    "metastasis": "cancer that has spread from where it originally started",
    "metastases": "multiple areas where cancer has spread",
    "edema": "swelling caused by fluid building up in the tissues",
    "stenosis": "a narrowing that restricts normal flow (blood, fluid, etc.)",
    "occlusion": "a complete blockage",
    "infarct": "tissue that has died due to lack of blood supply",
    "fracture": "a break or crack in a bone",
    "consolidation": "part of the lung is filled with something (like fluid or infection) instead of air",
    "infiltrate": "an abnormal substance has entered the lung tissue",
    "thickening": "a lining or wall is thicker than normal",
    "adenopathy": "lymph nodes are swollen or enlarged",
    "lymphadenopathy": "multiple lymph nodes are swollen — the body may be fighting an infection or something else",
    "atherosclerosis": "build-up of fatty deposits in the walls of blood vessels — can narrow them over time",
    "fibrosis": "scar tissue has formed in the organ",
    "cirrhosis": "the liver has significant scarring — often from long-term damage",
    "hernia": "part of an organ or tissue has pushed through a weak spot in the surrounding muscle or tissue",
    "cyst": "a sac filled with fluid — often harmless but may need monitoring",
    "abscess": "a collection of pus caused by infection",
    "haematoma": "a collection of blood outside the blood vessels, usually from injury",
    "contusion": "bruising of the tissue or organ",
    "perfusion": "the flow of blood through an organ",
    "ischaemia": "reduced blood supply to a part of the body",
}

# DICOM tag names → index field names
DICOM_TAG_MAP: Dict[str, str] = {
    "PatientName": "patient_name",
    "PatientID": "patient_id",
    "PatientBirthDate": "dob",
    "PatientSex": "patient_sex",
    "PatientAge": "patient_age",
    "PatientSize": "patient_size",
    "PatientWeight": "patient_weight",
    "StudyDate": "study_date",
    "StudyTime": "study_time",
    "StudyDescription": "study_description",
    "SeriesDescription": "series_description",
    "Modality": "modality",
    "BodyPartExamined": "body_part",
    "InstitutionName": "institution",
    "ReferringPhysicianName": "referring_physician",
    "AccessionNumber": "accession_number",
    "StudyInstanceUID": "study_uid",
    "SeriesInstanceUID": "series_uid",
    "SOPInstanceUID": "sop_uid",
    "SOPClassUID": "sop_class_uid",
    "Manufacturer": "manufacturer",
    "ManufacturerModelName": "manufacturer_model_name",
    "NumberOfSeriesRelatedInstances": "num_images",
}

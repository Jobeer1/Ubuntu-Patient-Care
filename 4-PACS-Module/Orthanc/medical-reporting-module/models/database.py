#!/usr/bin/env python3
"""
Database models for Medical Reporting Module
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Report(db.Model):
    """Medical report model"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(50), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VoiceSession(db.Model):
    """Voice session model"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.String(50), nullable=False)
    transcription = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def init_db():
    """Initialize database"""
    db.create_all()
    seed_medical_terms()

def seed_medical_terms():
    """Seed database with medical terms"""
    from .training_data import MedicalTerm
    
    # Check if terms already exist
    if MedicalTerm.query.first():
        return
    
    medical_categories = {
        "anatomy": [
            "cardiovascular system", "respiratory system", "gastrointestinal tract",
            "central nervous system", "musculoskeletal system", "genitourinary system",
            "endocrine system", "lymphatic system", "integumentary system"
        ],
        "conditions": [
            "hypertension", "diabetes mellitus", "myocardial infarction",
            "pneumonia", "tuberculosis", "HIV/AIDS", "chronic kidney disease",
            "asthma", "chronic obstructive pulmonary disease", "stroke"
        ],
        "procedures": [
            "chest X-ray", "CT scan", "MRI scan", "echocardiogram",
            "electrocardiogram", "blood pressure measurement", "pulse oximetry",
            "ultrasound", "endoscopy", "biopsy"
        ],
        "medications": [
            "antihypertensives", "antibiotics", "analgesics", "antiretrovirals",
            "bronchodilators", "diuretics", "beta-blockers", "ACE inhibitors",
            "insulin", "anticoagulants"
        ],
        "sa_specific": [
            "clinic sister", "community health worker", "traditional healer",
            "motor vehicle accident", "gunshot wound", "traditional medicine",
            "sangoma", "muti", "clinic", "district hospital"
        ]
    }
    
    for category, terms in medical_categories.items():
        for term in terms:
            medical_term = MedicalTerm(
                term=term,
                category=category,
                difficulty_level=1 if category == "sa_specific" else 2
            )
            db.session.add(medical_term)
    
    try:
        db.session.commit()
        print(f"Seeded {sum(len(terms) for terms in medical_categories.values())} medical terms")
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding medical terms: {e}")
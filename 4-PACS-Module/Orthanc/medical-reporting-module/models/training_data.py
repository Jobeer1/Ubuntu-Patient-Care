#!/usr/bin/env python3
"""
Training Data Models for Medical STT Enhancements
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from .database import db

class TrainingSession(db.Model):
    """User training sessions for medical terminology"""
    __tablename__ = 'training_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    medical_term = db.Column(db.String(200), nullable=False)
    audio_path = db.Column(db.String(500))
    audio_features = db.Column(db.LargeBinary)
    expected_transcription = db.Column(db.Text)
    actual_transcription = db.Column(db.Text)
    accuracy_score = db.Column(db.Float, default=0.0)
    session_date = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(100))

class MedicalTerm(db.Model):
    """Medical terms database with categories"""
    __tablename__ = 'medical_terms'
    
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(200), unique=True, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    pronunciation_guide = db.Column(db.Text)
    common_variations = db.Column(db.Text)
    difficulty_level = db.Column(db.Integer, default=1)

class UserTrainingProgress(db.Model):
    """User training progress tracking"""
    __tablename__ = 'user_training_progress'
    
    user_id = db.Column(db.String(50), primary_key=True)
    total_sessions = db.Column(db.Integer, default=0)
    accuracy_improvement = db.Column(db.Float, default=0.0)
    last_training_date = db.Column(db.DateTime)
    problematic_terms = db.Column(db.Text)  # JSON array
    completed_categories = db.Column(db.Text)  # JSON array
    
    def get_problematic_terms(self):
        """Get problematic terms as list"""
        if self.problematic_terms:
            return json.loads(self.problematic_terms)
        return []
    
    def set_problematic_terms(self, terms):
        """Set problematic terms from list"""
        self.problematic_terms = json.dumps(terms)
    
    def get_completed_categories(self):
        """Get completed categories as list"""
        if self.completed_categories:
            return json.loads(self.completed_categories)
        return []
    
    def set_completed_categories(self, categories):
        """Set completed categories from list"""
        self.completed_categories = json.dumps(categories)

class TrainingDataStore:
    """Training data management class"""
    
    def __init__(self, user_id):
        self.user_id = user_id
    
    def store_training_session(self, term, audio_features, accuracy_score, category=None, 
                             expected_transcription=None, actual_transcription=None):
        """Store training session data for model improvement"""
        session = TrainingSession(
            user_id=self.user_id,
            medical_term=term,
            audio_features=audio_features,
            accuracy_score=accuracy_score,
            category=category,
            expected_transcription=expected_transcription,
            actual_transcription=actual_transcription
        )
        
        db.session.add(session)
        
        # Update user progress
        progress = UserTrainingProgress.query.filter_by(user_id=self.user_id).first()
        if not progress:
            progress = UserTrainingProgress(user_id=self.user_id)
            db.session.add(progress)
        
        progress.total_sessions += 1
        progress.last_training_date = datetime.utcnow()
        
        # Update accuracy improvement (simple average for now)
        if progress.total_sessions > 1:
            progress.accuracy_improvement = (progress.accuracy_improvement + accuracy_score) / 2
        else:
            progress.accuracy_improvement = accuracy_score
        
        db.session.commit()
        return session
    
    def get_user_training_progress(self):
        """Retrieve user's training progress and statistics"""
        progress = UserTrainingProgress.query.filter_by(user_id=self.user_id).first()
        if not progress:
            return {
                'total_sessions': 0,
                'accuracy_improvement': 0.0,
                'last_training_date': None,
                'problematic_terms': [],
                'completed_categories': []
            }
        
        return {
            'total_sessions': progress.total_sessions,
            'accuracy_improvement': progress.accuracy_improvement,
            'last_training_date': progress.last_training_date,
            'problematic_terms': progress.get_problematic_terms(),
            'completed_categories': progress.get_completed_categories()
        }
    
    def get_problematic_terms(self):
        """Identify terms that need additional training"""
        # Get terms with low accuracy scores
        sessions = TrainingSession.query.filter_by(user_id=self.user_id).filter(
            TrainingSession.accuracy_score < 0.7
        ).all()
        
        problematic = {}
        for session in sessions:
            term = session.medical_term
            if term not in problematic:
                problematic[term] = {
                    'term': term,
                    'category': session.category,
                    'attempts': 0,
                    'avg_accuracy': 0.0
                }
            
            problematic[term]['attempts'] += 1
            problematic[term]['avg_accuracy'] = (
                problematic[term]['avg_accuracy'] + session.accuracy_score
            ) / problematic[term]['attempts']
        
        return list(problematic.values())
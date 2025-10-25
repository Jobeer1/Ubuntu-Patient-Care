#!/usr/bin/env python3
"""
Voice Shortcuts Models for Medical STT Enhancements
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from .database import db

class VoiceShortcut(db.Model):
    """Voice shortcuts for quick template access"""
    __tablename__ = 'voice_shortcuts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    shortcut_name = db.Column(db.String(100), nullable=False)
    audio_features = db.Column(db.LargeBinary, nullable=False)
    template_id = db.Column(db.String(100))
    template_content = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    usage_count = db.Column(db.Integer, default=0)
    accuracy_score = db.Column(db.Float, default=0.0)

class ShortcutUsage(db.Model):
    """Shortcut usage analytics"""
    __tablename__ = 'shortcut_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    shortcut_id = db.Column(db.Integer, db.ForeignKey('voice_shortcuts.id'), nullable=False)
    user_id = db.Column(db.String(50), nullable=False)
    used_date = db.Column(db.DateTime, default=datetime.utcnow)
    match_confidence = db.Column(db.Float)
    success = db.Column(db.Boolean, default=True)
    
    shortcut = db.relationship('VoiceShortcut', backref=db.backref('usage_records', lazy=True))

class VoiceShortcutStore:
    """Voice shortcut management class"""
    
    def __init__(self, user_id):
        self.user_id = user_id
    
    def create_shortcut(self, name, audio_features, template_id=None, template_content=None):
        """Create new voice shortcut"""
        shortcut = VoiceShortcut(
            user_id=self.user_id,
            shortcut_name=name,
            audio_features=audio_features,
            template_id=template_id,
            template_content=template_content
        )
        
        db.session.add(shortcut)
        db.session.commit()
        return shortcut
    
    def get_user_shortcuts(self):
        """Retrieve all shortcuts for a user"""
        shortcuts = VoiceShortcut.query.filter_by(user_id=self.user_id).order_by(
            VoiceShortcut.usage_count.desc()
        ).all()
        
        return [{
            'id': s.id,
            'name': s.shortcut_name,
            'template_id': s.template_id,
            'template_content': s.template_content,
            'created_date': s.created_date,
            'last_used': s.last_used,
            'usage_count': s.usage_count,
            'accuracy_score': s.accuracy_score
        } for s in shortcuts]
    
    def update_shortcut(self, shortcut_id, name=None, template_id=None, template_content=None):
        """Update an existing shortcut"""
        shortcut = VoiceShortcut.query.filter_by(
            id=shortcut_id, user_id=self.user_id
        ).first()
        
        if not shortcut:
            return None
        
        if name:
            shortcut.shortcut_name = name
        if template_id:
            shortcut.template_id = template_id
        if template_content:
            shortcut.template_content = template_content
        
        db.session.commit()
        return shortcut
    
    def delete_shortcut(self, shortcut_id):
        """Delete a voice shortcut"""
        shortcut = VoiceShortcut.query.filter_by(
            id=shortcut_id, user_id=self.user_id
        ).first()
        
        if not shortcut:
            return False
        
        # Delete usage records first
        ShortcutUsage.query.filter_by(shortcut_id=shortcut_id).delete()
        
        # Delete shortcut
        db.session.delete(shortcut)
        db.session.commit()
        return True
    
    def record_usage(self, shortcut_id, match_confidence, success=True):
        """Record shortcut usage for analytics"""
        shortcut = VoiceShortcut.query.filter_by(
            id=shortcut_id, user_id=self.user_id
        ).first()
        
        if not shortcut:
            return False
        
        # Update shortcut stats
        shortcut.usage_count += 1
        shortcut.last_used = datetime.utcnow()
        
        # Update accuracy score (running average)
        if shortcut.accuracy_score == 0.0:
            shortcut.accuracy_score = match_confidence
        else:
            shortcut.accuracy_score = (shortcut.accuracy_score + match_confidence) / 2
        
        # Record usage
        usage = ShortcutUsage(
            shortcut_id=shortcut_id,
            user_id=self.user_id,
            match_confidence=match_confidence,
            success=success
        )
        
        db.session.add(usage)
        db.session.commit()
        return True
    
    def get_shortcut_by_id(self, shortcut_id):
        """Get shortcut by ID"""
        return VoiceShortcut.query.filter_by(
            id=shortcut_id, user_id=self.user_id
        ).first()
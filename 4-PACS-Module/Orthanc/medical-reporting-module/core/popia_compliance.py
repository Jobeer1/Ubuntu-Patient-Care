#!/usr/bin/env python3
"""
POPIA Compliance Manager for Medical STT System
Handles data protection, retention policies, and user rights
"""

import logging
from datetime import datetime, timedelta
from models.database import db
from models.training_data import TrainingSession, UserTrainingProgress
from models.voice_shortcuts import VoiceShortcut, ShortcutUsage
from core.user_manager import User, UserSession
from core.secure_audio_handler import secure_audio_handler

logger = logging.getLogger(__name__)

class POPIACompliance:
    """POPIA compliance management for medical data"""
    
    # Data retention periods (in days)
    TRAINING_DATA_RETENTION = 365 * 7  # 7 years for medical training data
    VOICE_SHORTCUTS_RETENTION = 365 * 5  # 5 years for voice shortcuts
    AUDIO_FILES_RETENTION = 1  # 1 day for temporary audio files
    SESSION_DATA_RETENTION = 90  # 90 days for session logs
    
    @staticmethod
    def get_user_data_summary(user_id):
        """Get comprehensive summary of user's stored data"""
        try:
            summary = {
                'user_id': user_id,
                'generated_at': datetime.utcnow().isoformat(),
                'data_categories': {}
            }
            
            # User profile data
            user = User.query.filter_by(id=user_id).first()
            if user:
                summary['data_categories']['profile'] = {
                    'username': user.username,
                    'email': user.email,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                    'role': user.role,
                    'consent_date': user.consent_date.isoformat() if user.consent_date else None,
                    'data_retention_date': user.data_retention_date.isoformat() if user.data_retention_date else None
                }
            
            # Training data
            training_sessions = TrainingSession.query.filter_by(user_id=user_id).all()
            summary['data_categories']['training_sessions'] = {
                'count': len(training_sessions),
                'sessions': [{
                    'id': session.id,
                    'medical_term': session.medical_term,
                    'category': session.category,
                    'session_date': session.session_date.isoformat() if session.session_date else None,
                    'accuracy_score': session.accuracy_score
                } for session in training_sessions]
            }
            
            # Training progress
            progress = UserTrainingProgress.query.filter_by(user_id=user_id).first()
            if progress:
                summary['data_categories']['training_progress'] = {
                    'total_sessions': progress.total_sessions,
                    'accuracy_improvement': progress.accuracy_improvement,
                    'last_training_date': progress.last_training_date.isoformat() if progress.last_training_date else None,
                    'problematic_terms': progress.get_problematic_terms(),
                    'completed_categories': progress.get_completed_categories()
                }
            
            # Voice shortcuts
            shortcuts = VoiceShortcut.query.filter_by(user_id=user_id).all()
            summary['data_categories']['voice_shortcuts'] = {
                'count': len(shortcuts),
                'shortcuts': [{
                    'id': shortcut.id,
                    'name': shortcut.shortcut_name,
                    'template_id': shortcut.template_id,
                    'created_date': shortcut.created_date.isoformat() if shortcut.created_date else None,
                    'last_used': shortcut.last_used.isoformat() if shortcut.last_used else None,
                    'usage_count': shortcut.usage_count
                } for shortcut in shortcuts]
            }
            
            # Session data
            sessions = UserSession.query.filter_by(user_id=user_id).all()
            summary['data_categories']['sessions'] = {
                'count': len(sessions),
                'sessions': [{
                    'id': session.id,
                    'created_at': session.created_at.isoformat() if session.created_at else None,
                    'last_activity': session.last_activity.isoformat() if session.last_activity else None,
                    'ip_address': session.ip_address,
                    'is_active': session.is_active
                } for session in sessions]
            }
            
            # Audio file statistics
            audio_stats = secure_audio_handler.get_user_audio_stats(user_id)
            summary['data_categories']['audio_files'] = audio_stats
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate user data summary: {e}")
            return None
    
    @staticmethod
    def export_user_data(user_id, format='json'):
        """Export user data for POPIA data portability right"""
        try:
            summary = POPIACompliance.get_user_data_summary(user_id)
            if not summary:
                return None
            
            if format.lower() == 'json':
                import json
                return json.dumps(summary, indent=2, ensure_ascii=False)
            
            elif format.lower() == 'csv':
                # Create CSV export for structured data
                import csv
                import io
                
                output = io.StringIO()
                
                # Export training sessions
                if summary['data_categories'].get('training_sessions'):
                    writer = csv.writer(output)
                    writer.writerow(['Data Type', 'Training Sessions'])
                    writer.writerow(['Session ID', 'Medical Term', 'Category', 'Date', 'Accuracy Score'])
                    
                    for session in summary['data_categories']['training_sessions']['sessions']:
                        writer.writerow([
                            session['id'],
                            session['medical_term'],
                            session['category'],
                            session['session_date'],
                            session['accuracy_score']
                        ])
                    
                    writer.writerow([])  # Empty row
                
                # Export voice shortcuts
                if summary['data_categories'].get('voice_shortcuts'):
                    writer.writerow(['Data Type', 'Voice Shortcuts'])
                    writer.writerow(['Shortcut ID', 'Name', 'Template ID', 'Created Date', 'Usage Count'])
                    
                    for shortcut in summary['data_categories']['voice_shortcuts']['shortcuts']:
                        writer.writerow([
                            shortcut['id'],
                            shortcut['name'],
                            shortcut['template_id'],
                            shortcut['created_date'],
                            shortcut['usage_count']
                        ])
                
                return output.getvalue()
            
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to export user data: {e}")
            return None
    
    @staticmethod
    def delete_user_data(user_id, data_categories=None):
        """Delete user data for POPIA right to erasure"""
        try:
            deleted_items = {
                'training_sessions': 0,
                'voice_shortcuts': 0,
                'shortcut_usage': 0,
                'training_progress': 0,
                'sessions': 0,
                'audio_files': False,
                'user_profile': False
            }
            
            categories_to_delete = data_categories or [
                'training_sessions', 'voice_shortcuts', 'shortcut_usage',
                'training_progress', 'sessions', 'audio_files'
            ]
            
            # Delete training sessions
            if 'training_sessions' in categories_to_delete:
                sessions = TrainingSession.query.filter_by(user_id=user_id).all()
                for session in sessions:
                    db.session.delete(session)
                deleted_items['training_sessions'] = len(sessions)
            
            # Delete voice shortcuts and usage
            if 'voice_shortcuts' in categories_to_delete:
                shortcuts = VoiceShortcut.query.filter_by(user_id=user_id).all()
                for shortcut in shortcuts:
                    # Delete usage records first
                    usage_records = ShortcutUsage.query.filter_by(shortcut_id=shortcut.id).all()
                    for usage in usage_records:
                        db.session.delete(usage)
                    deleted_items['shortcut_usage'] += len(usage_records)
                    
                    # Delete shortcut
                    db.session.delete(shortcut)
                deleted_items['voice_shortcuts'] = len(shortcuts)
            
            # Delete training progress
            if 'training_progress' in categories_to_delete:
                progress = UserTrainingProgress.query.filter_by(user_id=user_id).first()
                if progress:
                    db.session.delete(progress)
                    deleted_items['training_progress'] = 1
            
            # Delete user sessions
            if 'sessions' in categories_to_delete:
                sessions = UserSession.query.filter_by(user_id=user_id).all()
                for session in sessions:
                    db.session.delete(session)
                deleted_items['sessions'] = len(sessions)
            
            # Delete audio files
            if 'audio_files' in categories_to_delete:
                deleted_items['audio_files'] = secure_audio_handler.delete_user_audio_data(user_id)
            
            # Delete user profile (only if explicitly requested)
            if 'user_profile' in categories_to_delete:
                user = User.query.filter_by(id=user_id).first()
                if user:
                    db.session.delete(user)
                    deleted_items['user_profile'] = True
            
            db.session.commit()
            
            logger.info(f"Deleted user data for {user_id}: {deleted_items}")
            return deleted_items
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete user data: {e}")
            return None
    
    @staticmethod
    def apply_retention_policy():
        """Apply data retention policies across all users"""
        try:
            current_time = datetime.utcnow()
            retention_summary = {
                'training_sessions_deleted': 0,
                'voice_shortcuts_deleted': 0,
                'sessions_deleted': 0,
                'audio_files_cleaned': 0
            }
            
            # Clean up old training sessions
            training_cutoff = current_time - timedelta(days=POPIACompliance.TRAINING_DATA_RETENTION)
            old_training = TrainingSession.query.filter(
                TrainingSession.session_date < training_cutoff
            ).all()
            
            for session in old_training:
                db.session.delete(session)
            retention_summary['training_sessions_deleted'] = len(old_training)
            
            # Clean up old voice shortcuts
            shortcuts_cutoff = current_time - timedelta(days=POPIACompliance.VOICE_SHORTCUTS_RETENTION)
            old_shortcuts = VoiceShortcut.query.filter(
                VoiceShortcut.created_date < shortcuts_cutoff
            ).all()
            
            for shortcut in old_shortcuts:
                # Delete usage records first
                ShortcutUsage.query.filter_by(shortcut_id=shortcut.id).delete()
                db.session.delete(shortcut)
            retention_summary['voice_shortcuts_deleted'] = len(old_shortcuts)
            
            # Clean up old sessions
            sessions_cutoff = current_time - timedelta(days=POPIACompliance.SESSION_DATA_RETENTION)
            old_sessions = UserSession.query.filter(
                UserSession.created_at < sessions_cutoff
            ).all()
            
            for session in old_sessions:
                db.session.delete(session)
            retention_summary['sessions_deleted'] = len(old_sessions)
            
            # Clean up audio files
            retention_summary['audio_files_cleaned'] = secure_audio_handler.cleanup_expired_files()
            
            db.session.commit()
            
            logger.info(f"Applied retention policy: {retention_summary}")
            return retention_summary
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to apply retention policy: {e}")
            return None
    
    @staticmethod
    def update_user_consent(user_id, consent_granted, retention_period_years=7):
        """Update user consent for data processing"""
        try:
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return False
            
            user.data_retention_consent = consent_granted
            user.consent_date = datetime.utcnow()
            
            if consent_granted:
                user.data_retention_date = datetime.utcnow() + timedelta(days=365 * retention_period_years)
            else:
                user.data_retention_date = datetime.utcnow()  # Immediate deletion
            
            db.session.commit()
            
            logger.info(f"Updated consent for user {user_id}: {consent_granted}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update user consent: {e}")
            return False
    
    @staticmethod
    def get_consent_status(user_id):
        """Get user's current consent status"""
        try:
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return None
            
            return {
                'user_id': user_id,
                'consent_granted': user.data_retention_consent,
                'consent_date': user.consent_date.isoformat() if user.consent_date else None,
                'retention_date': user.data_retention_date.isoformat() if user.data_retention_date else None,
                'days_until_deletion': (user.data_retention_date - datetime.utcnow()).days if user.data_retention_date else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get consent status: {e}")
            return None
    
    @staticmethod
    def anonymize_user_data(user_id):
        """Anonymize user data while preserving research value"""
        try:
            # Generate anonymous ID
            import hashlib
            anonymous_id = hashlib.sha256(f"anon_{user_id}".encode()).hexdigest()[:16]
            
            anonymized_count = 0
            
            # Anonymize training sessions
            sessions = TrainingSession.query.filter_by(user_id=user_id).all()
            for session in sessions:
                session.user_id = anonymous_id
                anonymized_count += 1
            
            # Anonymize voice shortcuts (remove personal identifiers)
            shortcuts = VoiceShortcut.query.filter_by(user_id=user_id).all()
            for shortcut in shortcuts:
                shortcut.user_id = anonymous_id
                # Remove template content that might contain personal info
                shortcut.template_content = "[ANONYMIZED]"
                anonymized_count += 1
            
            # Anonymize training progress
            progress = UserTrainingProgress.query.filter_by(user_id=user_id).first()
            if progress:
                progress.user_id = anonymous_id
                anonymized_count += 1
            
            # Delete user sessions (contain IP addresses)
            UserSession.query.filter_by(user_id=user_id).delete()
            
            # Delete audio files (contain voice biometrics)
            secure_audio_handler.delete_user_audio_data(user_id)
            
            # Mark user as anonymized
            user = User.query.filter_by(id=user_id).first()
            if user:
                user.username = f"anonymized_{anonymous_id}"
                user.email = f"anonymized_{anonymous_id}@deleted.local"
                user.is_active = False
            
            db.session.commit()
            
            logger.info(f"Anonymized {anonymized_count} records for user {user_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to anonymize user data: {e}")
            return False

# Convenience functions
def get_user_data_export(user_id, format='json'):
    """Export user data in specified format"""
    return POPIACompliance.export_user_data(user_id, format)

def delete_user_data(user_id, categories=None):
    """Delete user data categories"""
    return POPIACompliance.delete_user_data(user_id, categories)

def apply_retention_policy():
    """Apply data retention policies"""
    return POPIACompliance.apply_retention_policy()

def update_consent(user_id, granted, years=7):
    """Update user consent"""
    return POPIACompliance.update_user_consent(user_id, granted, years)
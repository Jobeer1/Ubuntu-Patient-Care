"""
Copilot AI Module
================
GitHub Copilot intent recognition and response generation
Handles user intents and generates AI-powered responses
"""

import re
from datetime import datetime, timedelta
from app_modules.config import ThemeConfig, ResponseTemplates
from app_modules.database import db
from app_modules.utils import safe_json_dump, log_info, get_current_datetime

# ============================================================================
# INTENT MATCHING
# ============================================================================

class IntentMatcher:
    """Match user input to intent categories"""
    
    # Intent patterns (keyword-based)
    INTENT_PATTERNS = {
        'appointment': {
            'keywords': ['appointment', 'schedule', 'book', 'meeting', 'visit', 'consult', 'doctor', 'when', 'available'],
            'confidence_boost': ['when can', 'book appointment', 'schedule visit', 'see doctor']
        },
        'form_filling': {
            'keywords': ['form', 'fill', 'complete', 'application', 'paperwork', 'document', 'submit'],
            'confidence_boost': ['help fill', 'auto fill', 'fill form', 'complete application']
        },
        'benefits': {
            'keywords': ['benefit', 'coverage', 'insurance', 'plan', 'copay', 'deductible', 'covered'],
            'confidence_boost': ['insurance benefit', 'what covered', 'my benefits', 'deductible']
        },
        'pre_authorization': {
            'keywords': ['pre-auth', 'authorization', 'approval', 'pre-approval', 'authorized', 'approved'],
            'confidence_boost': ['pre-authorization', 'need approval', 'waiting for approval']
        },
        'records': {
            'keywords': ['record', 'history', 'medical', 'result', 'test', 'lab', 'previous'],
            'confidence_boost': ['medical records', 'test results', 'past visits']
        },
        'profile': {
            'keywords': ['profile', 'account', 'settings', 'information', 'personal', 'update', 'change'],
            'confidence_boost': ['update profile', 'change information', 'account settings']
        },
        'help': {
            'keywords': ['help', 'assist', 'how', 'what', 'where', 'guide', 'support', 'confused'],
            'confidence_boost': ['how do', 'how can', 'help me']
        }
    }
    
    @staticmethod
    def match_intent(user_input):
        """Match user input to intent with confidence score"""
        
        user_input_lower = user_input.lower()
        scores = {}
        
        for intent, patterns in IntentMatcher.INTENT_PATTERNS.items():
            score = 0
            
            # Check confidence boost patterns first (higher weight)
            for pattern in patterns['confidence_boost']:
                if pattern in user_input_lower:
                    score += 3
            
            # Check regular keywords
            for keyword in patterns['keywords']:
                if keyword in user_input_lower:
                    score += 1
            
            if score > 0:
                scores[intent] = score
        
        if not scores:
            return 'help', 0.0
        
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        confidence = min(1.0, best_score / 5.0)
        
        return best_intent, confidence
    
    @staticmethod
    def extract_entities(user_input, intent):
        """Extract relevant entities from user input"""
        
        entities = {}
        user_input_lower = user_input.lower()
        
        # Extract date references
        if any(word in user_input_lower for word in ['tomorrow', 'next week', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
            entities['date_reference'] = True
        
        # Extract time references
        if any(word in user_input_lower for word in ['morning', 'afternoon', 'evening', 'am', 'pm', 'o\'clock']):
            entities['time_reference'] = True
        
        # Extract doctor type references
        if any(word in user_input_lower for word in ['cardiologist', 'neurologist', 'dermatologist', 'pediatrician', 'orthopedic', 'surgeon', 'therapist', 'specialist']):
            entities['doctor_specialty'] = True
        
        # Extract document types
        if any(word in user_input_lower for word in ['id', 'passport', 'license', 'insurance card', 'authorization form']):
            entities['document_type'] = True
        
        return entities


# ============================================================================
# RESPONSE GENERATION
# ============================================================================

class ResponseGenerator:
    """Generate AI responses for different intents"""
    
    RESPONSE_TEMPLATES = {
        'appointment': {
            'initial': "I'd be happy to help you schedule an appointment. Let me provide you with available time slots.",
            'action': 'show_appointment_booking',
            'follow_up': [
                "What specialty would you prefer - General Practice, Cardiology, or Orthopedics?",
                "Do you prefer morning or afternoon appointments?",
                "Are you available on weekdays or would you prefer a weekend appointment?"
            ]
        },
        'form_filling': {
            'initial': "I can help you complete your medical forms quickly and accurately.",
            'action': 'show_form_auto_fill',
            'follow_up': [
                "Which form do you need to complete? Patient intake, insurance authorization, or medical history?",
                "I can auto-populate your personal information to save time.",
                "Are there any specific fields you'd like help with?"
            ]
        },
        'benefits': {
            'initial': "Let me check your insurance benefits and coverage details.",
            'action': 'show_benefits_card',
            'follow_up': [
                "Your current plan covers preventive care at 100%.",
                "Specialist visits have a $50 copay.",
                "What specific service are you asking about?"
            ]
        },
        'pre_authorization': {
            'initial': "I can help you track and manage your pre-authorization requests.",
            'action': 'show_pre_auth_tracker',
            'follow_up': [
                "Checking your authorization status with your insurance provider...",
                "Your MRI authorization is pending (submitted 2 days ago).",
                "Would you like me to follow up with your insurance company?"
            ]
        },
        'records': {
            'initial': "Let me retrieve your medical records and test results.",
            'action': 'show_medical_records',
            'follow_up': [
                "Your latest blood work results are available.",
                "You have 12 previous appointment records on file.",
                "Would you like to download or share any of these records?"
            ]
        },
        'profile': {
            'initial': "I can help you update your profile information.",
            'action': 'show_profile_settings',
            'follow_up': [
                "What information would you like to update - contact details, emergency contacts, or medical history?",
                "Your profile information is current and complete.",
                "Would you like to add any additional medical providers?"
            ]
        },
        'help': {
            'initial': "I'm here to help! Here's what I can assist with:",
            'action': None,
            'follow_up': [
                "📅 Schedule appointments",
                "📋 Fill out forms automatically",
                "🏥 Check insurance benefits",
                "✅ Track pre-authorizations",
                "📄 Access medical records",
                "👤 Manage your profile"
            ]
        }
    }
    
    @staticmethod
    def generate_response(user_input, user_id, intent=None, entities=None):
        """Generate AI response"""
        
        # Match intent if not provided
        if not intent:
            intent, confidence = IntentMatcher.match_intent(user_input)
        
        if not entities:
            entities = IntentMatcher.extract_entities(user_input, intent)
        
        # Get template
        template = ResponseGenerator.RESPONSE_TEMPLATES.get(intent, ResponseGenerator.RESPONSE_TEMPLATES['help'])
        
        # Build response
        response = {
            'intent': intent,
            'initial_message': template['initial'],
            'action': template['action'],
            'follow_up_suggestions': template['follow_up'][:2],
            'entities': entities,
            'timestamp': get_current_datetime().isoformat()
        }
        
        # Save chat history
        db.chat.save_chat({
            'user_id': user_id,
            'user_message': user_input,
            'copilot_response': response['initial_message'],
            'intent': intent,
            'action': template['action']
        })
        
        log_info(f"Copilot response generated for user {user_id}: intent={intent}")
        
        return response
    
    @staticmethod
    def handle_conversation(user_id, user_input, conversation_history=None):
        """Handle multi-turn conversation"""
        
        # Get conversation context
        if not conversation_history:
            conversation_history = db.chat.get_chat_history(user_id, limit=5)
        
        # Match intent
        intent, confidence = IntentMatcher.match_intent(user_input)
        
        # Adjust response based on conversation history
        if conversation_history and len(conversation_history) > 0:
            last_action = conversation_history[-1].get('action')
            
            # If same intent in sequence, provide more specific help
            if last_action == intent:
                response = ResponseGenerator._get_follow_up_response(intent, user_input)
            else:
                response = ResponseGenerator.generate_response(user_input, user_id, intent)
        else:
            response = ResponseGenerator.generate_response(user_input, user_id, intent)
        
        return response
    
    @staticmethod
    def _get_follow_up_response(intent, user_input):
        """Get follow-up response for continuing conversation"""
        
        template = ResponseGenerator.RESPONSE_TEMPLATES.get(intent)
        
        if not template:
            return ResponseGenerator.RESPONSE_TEMPLATES['help']
        
        # Generate contextual response
        response = {
            'intent': intent,
            'initial_message': f"I understood you're asking about {intent}. Let me provide more details...",
            'action': template['action'],
            'follow_up_suggestions': template['follow_up'],
            'timestamp': get_current_datetime().isoformat()
        }
        
        return response
    
    @staticmethod
    def get_appointment_suggestions(user_id):
        """Get appointment scheduling suggestions"""
        
        user = db.users.get_user_by_id(user_id)
        
        suggestions = {
            'available_slots': [
                {'date': '2024-01-15', 'time': '09:00 AM', 'doctor': 'Dr. Smith', 'specialty': 'General Practice'},
                {'date': '2024-01-15', 'time': '02:00 PM', 'doctor': 'Dr. Johnson', 'specialty': 'Cardiology'},
                {'date': '2024-01-16', 'time': '10:30 AM', 'doctor': 'Dr. Williams', 'specialty': 'Orthopedics'}
            ],
            'preferred_doctor': None,
            'last_visit': None
        }
        
        # Get last appointment
        appointments = db.appointments.get_user_appointments(user_id)
        if appointments:
            suggestions['last_visit'] = appointments[-1]
        
        return suggestions
    
    @staticmethod
    def get_insurance_summary(user_id):
        """Get insurance benefits summary"""
        
        return {
            'plan_name': 'Premium Health Plus',
            'copay': {
                'primary_care': '$25',
                'specialist': '$50',
                'emergency': '$250'
            },
            'deductible': {
                'individual': '$1,500',
                'family': '$3,000',
                'met': '$750'
            },
            'coverage': {
                'preventive': '100%',
                'inpatient': '80%',
                'outpatient': '70%'
            },
            'coverage_start': '2024-01-01',
            'coverage_end': '2024-12-31'
        }


# ============================================================================
# ACTION MAPPER
# ============================================================================

class ActionMapper:
    """Map intents to UI actions"""
    
    ACTION_MAPPING = {
        'show_appointment_booking': {
            'component': 'AppointmentBooking',
            'properties': {
                'step': 'select_specialty',
                'show_calendar': True,
                'auto_fill': True
            }
        },
        'show_form_auto_fill': {
            'component': 'FormAutoFill',
            'properties': {
                'form_type': 'patient_intake',
                'auto_populate': True,
                'save_draft': True
            }
        },
        'show_benefits_card': {
            'component': 'InsuranceBenefits',
            'properties': {
                'show_details': True,
                'expand_coverage': True
            }
        },
        'show_pre_auth_tracker': {
            'component': 'PreAuthorizationTracker',
            'properties': {
                'show_all': True,
                'refresh_status': True
            }
        },
        'show_medical_records': {
            'component': 'MedicalRecords',
            'properties': {
                'sort_by': 'date_desc',
                'filter': 'all'
            }
        },
        'show_profile_settings': {
            'component': 'ProfileSettings',
            'properties': {
                'tab': 'personal_info',
                'edit_mode': False
            }
        }
    }
    
    @staticmethod
    def get_action_for_intent(intent):
        """Get UI action for intent"""
        
        template = ResponseGenerator.RESPONSE_TEMPLATES.get(intent)
        
        if not template or not template.get('action'):
            return None
        
        action = template['action']
        return ActionMapper.ACTION_MAPPING.get(action, {})


# ============================================================================
# COPILOT MAIN
# ============================================================================

class Copilot:
    """Main Copilot AI assistant"""
    
    @staticmethod
    def chat(user_id, user_input):
        """Process user chat input and return AI response"""
        
        # Match intent
        intent, confidence = IntentMatcher.match_intent(user_input)
        
        # Extract entities
        entities = IntentMatcher.extract_entities(user_input, intent)
        
        # Generate response
        response = ResponseGenerator.generate_response(user_input, user_id, intent, entities)
        
        # Get action mapping
        action_data = ActionMapper.get_action_for_intent(intent)
        
        response['action_data'] = action_data
        response['confidence'] = confidence
        
        return response
    
    @staticmethod
    def get_context(user_id):
        """Get user context for better responses"""
        
        user = db.users.get_user_by_id(user_id)
        
        context = {
            'user_name': user.get('name', ''),
            'user_role': user.get('role', 'patient'),
            'last_login': user.get('last_login'),
            'recent_appointments': db.appointments.get_user_appointments(user_id, limit=3),
            'recent_authorizations': db.authorizations.get_user_authorizations(user_id, limit=3),
            'recent_chats': db.chat.get_chat_history(user_id, limit=5)
        }
        
        return context
    
    @staticmethod
    def suggest_next_action(user_id):
        """Suggest next action based on user context"""
        
        context = Copilot.get_context(user_id)
        
        # Suggest based on recent activity
        if not context['recent_appointments']:
            return {
                'suggestion': 'Schedule an appointment',
                'action': 'show_appointment_booking',
                'reason': 'No recent appointments found'
            }
        
        if context['recent_authorizations']:
            pending = [a for a in context['recent_authorizations'] if a.get('status') == 'pending']
            if pending:
                return {
                    'suggestion': 'Check pre-authorization status',
                    'action': 'show_pre_auth_tracker',
                    'reason': 'You have pending authorizations'
                }
        
        return {
            'suggestion': 'View your medical records',
            'action': 'show_medical_records',
            'reason': 'Keep your health information up to date'
        }

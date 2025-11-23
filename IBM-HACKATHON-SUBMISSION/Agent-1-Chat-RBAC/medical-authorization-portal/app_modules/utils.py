"""
Utilities Module - Helper Functions
===================================
Common utility functions used across the application
Password hashing, decorators, response formatting, etc.
"""

import hashlib
import uuid
import json
from functools import wraps
from datetime import datetime, timedelta
from flask import session, redirect, url_for, jsonify
from app_modules.config import SecurityConfig, ResponseTemplates

# ============================================================================
# PASSWORD & SECURITY UTILITIES
# ============================================================================

def hash_password(password):
    """Hash password using configured algorithm"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash

def generate_unique_id():
    """Generate unique ID"""
    return str(uuid.uuid4())

# ============================================================================
# DECORATORS
# ============================================================================

def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def json_required(f):
    """Decorator to require JSON request"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return error_response('Request must be JSON', 400)
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            from app_modules.database import db
            user = db.users.get_user_by_id(session['user_id'])
            
            if not user or user['role'] not in roles:
                return error_response('Insufficient permissions', 403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def handle_exceptions(f):
    """Decorator to handle exceptions with logging"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return error_response(f'Invalid value: {str(e)}', 400)
        except Exception as e:
            return error_response(f'Server error: {str(e)}', 500)
    return decorated_function

# ============================================================================
# RESPONSE FORMATTING
# ============================================================================

def success_response(data=None, message='Operation successful', status_code=200):
    """Format successful response"""
    response = {
        'success': True,
        'message': message,
        'data': data
    }
    return jsonify(response), status_code

def error_response(error, status_code=400, details=None):
    """Format error response"""
    response = {
        'success': False,
        'error': error,
        'details': details
    }
    return jsonify(response), status_code

def paginated_response(items, page=1, total=0, per_page=10):
    """Format paginated response"""
    return {
        'success': True,
        'data': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    }

# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_email(email):
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password meets requirements"""
    if len(password) < SecurityConfig.PASSWORD_MIN_LENGTH:
        return False, f'Password must be at least {SecurityConfig.PASSWORD_MIN_LENGTH} characters'
    
    # Add more validation rules as needed
    return True, 'Password is valid'

def validate_username(username):
    """Validate username format"""
    if len(username) < 3:
        return False, 'Username must be at least 3 characters'
    if len(username) > 50:
        return False, 'Username must be less than 50 characters'
    if not username.replace('_', '').replace('-', '').isalnum():
        return False, 'Username can only contain letters, numbers, underscores, and hyphens'
    return True, 'Username is valid'

# ============================================================================
# STRING & DATA UTILITIES
# ============================================================================

def truncate_string(s, length=50):
    """Truncate string to specified length"""
    return (s[:length] + '...') if len(s) > length else s

def safe_json_dump(obj, default='null'):
    """Safely serialize object to JSON"""
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return default

def safe_json_load(json_str):
    """Safely load JSON string"""
    try:
        return json.loads(json_str) if json_str else {}
    except (json.JSONDecodeError, TypeError):
        return {}

# ============================================================================
# DATETIME UTILITIES
# ============================================================================

def get_current_datetime():
    """Get current datetime"""
    return datetime.now()

def get_datetime_string(dt=None):
    """Get formatted datetime string"""
    dt = dt or datetime.now()
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def parse_datetime(dt_string):
    """Parse datetime string"""
    try:
        return datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return None

def is_datetime_expired(dt, hours=24):
    """Check if datetime has expired"""
    if not dt:
        return True
    delta = datetime.now() - dt
    return delta > timedelta(hours=hours)

# ============================================================================
# EMAIL UTILITIES
# ============================================================================

def extract_email_domain(email):
    """Extract domain from email"""
    try:
        return email.split('@')[1] if '@' in email else None
    except:
        return None

def get_email_name_part(email):
    """Get name part of email"""
    try:
        return email.split('@')[0] if '@' in email else None
    except:
        return None

# ============================================================================
# ROLE & PERMISSION UTILITIES
# ============================================================================

def detect_role_from_email(email):
    """Detect user role from email domain"""
    from app_modules.config import EmailDomainRoleMapping
    
    email_lower = email.lower()
    
    for pattern, role in EmailDomainRoleMapping.MAPPINGS.items():
        if pattern in email_lower:
            return role
    
    return EmailDomainRoleMapping.MAPPINGS.get('default', 'patient')

def has_permission(user, permission):
    """Check if user has specific permission"""
    from app_modules.config import RoleConfig
    
    user_role = user.get('role', 'patient')
    role_permissions = RoleConfig.ROLES.get(user_role, [])
    return permission in role_permissions

# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def log_info(message):
    """Log info message"""
    print(f"[INFO] {get_datetime_string()} - {message}")

def log_error(message, exception=None):
    """Log error message"""
    error_msg = f"[ERROR] {get_datetime_string()} - {message}"
    if exception:
        error_msg += f"\n        Exception: {str(exception)}"
    print(error_msg)

def log_debug(message):
    """Log debug message"""
    print(f"[DEBUG] {get_datetime_string()} - {message}")

def log_warning(message):
    """Log warning message"""
    print(f"[WARNING] {get_datetime_string()} - {message}")

# ============================================================================
# DICT & LIST UTILITIES
# ============================================================================

def safe_get(dict_obj, key, default=None):
    """Safely get dictionary value"""
    return dict_obj.get(key, default) if isinstance(dict_obj, dict) else default

def merge_dicts(dict1, dict2):
    """Merge two dictionaries"""
    result = dict1.copy()
    result.update(dict2)
    return result

def filter_dict(dict_obj, keys):
    """Filter dictionary to only include specified keys"""
    return {k: v for k, v in dict_obj.items() if k in keys}

def remove_dict_keys(dict_obj, keys):
    """Remove specified keys from dictionary"""
    return {k: v for k, v in dict_obj.items() if k not in keys}

# ============================================================================
# PAGINATION UTILITIES
# ============================================================================

def get_page_params():
    """Get page and per_page from request args"""
    from flask import request
    
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, int(request.args.get('per_page', 10)))
        return page, per_page
    except (ValueError, TypeError):
        return 1, 10

def paginate_list(items, page=1, per_page=10):
    """Paginate a list"""
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], len(items)

# ============================================================================
# FORMAT UTILITIES
# ============================================================================

def format_currency(amount, currency='R'):
    """Format amount as currency"""
    return f"{currency}{amount:,.2f}"

def format_percentage(value, total):
    """Format as percentage"""
    if total == 0:
        return 0
    return round((value / total) * 100, 2)

def format_phone(phone):
    """Format phone number"""
    # Remove non-digits
    digits = ''.join(c for c in phone if c.isdigit())
    
    # Format based on length
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11:
        return f"+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        return phone

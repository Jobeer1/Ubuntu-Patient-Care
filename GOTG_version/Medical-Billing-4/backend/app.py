"""
Medical Billing Module - Flask API
Gift of the Givers billing management and sustainability revenue tracking
"""

import os
import sqlite3
import logging
import jwt
from functools import wraps
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json

# Import billing modules
from insurance_intelligence import InsuranceIntelligenceEngine
from claims_processor import ClaimsProcessor
from sync_manager import MultiModuleSyncManager
from revenue_optimizer import RevenueOptimizer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DATABASE'] = os.environ.get('DATABASE_PATH', 'billing.db')

# Initialize billing engines
db_path = app.config['DATABASE']

# Create database if doesn't exist
def init_db():
    """Initialize database on startup"""
    if not os.path.exists(db_path):
        with open('schema.sql', 'r') as f:
            schema = f.read()
        
        conn = sqlite3.connect(db_path)
        conn.executescript(schema)
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {db_path}")

# Initialize on startup
init_db()

insurance_engine = InsuranceIntelligenceEngine(db_path)
claims_engine = ClaimsProcessor(db_path)
sync_manager = MultiModuleSyncManager(db_path)
revenue_optimizer = RevenueOptimizer(db_path)

# =====================================================
# AUTHENTICATION & MIDDLEWARE
# =====================================================

def token_required(f):
    """JWT token validation decorator (reused from RIS-1 pattern)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid authorization header'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data.get('user_id')
        except Exception as e:
            return jsonify({'error': f'Token validation failed: {str(e)}'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# =====================================================
# HEALTH & INFO ENDPOINTS
# =====================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'module': 'Medical-Billing-4',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/info', methods=['GET'])
def module_info():
    """Get module information"""
    return jsonify({
        'module_name': 'Medical-Billing-4',
        'description': 'Gift of the Givers medical billing and sustainability engine',
        'version': '1.0.0',
        'features': [
            'LLM-powered insurance verification',
            'Multi-format claim submission',
            'Offline-first operation',
            'Multi-module data sync',
            'Revenue tracking for sustainability'
        ],
        'capabilities': {
            'insurance_verification': True,
            'web_scraping': True,
            'offline_operation': True,
            'multi_module_sync': True,
            'revenue_tracking': True
        }
    }), 200

# =====================================================
# INSURANCE VERIFICATION ENDPOINTS
# =====================================================

@app.route('/api/insurance/verify', methods=['POST'])
@token_required
def verify_insurance(current_user):
    """
    Verify patient insurance using LLM-powered verification
    
    Request body:
    {
        "patient_name": "John Doe",
        "patient_dob": "1980-01-01",
        "member_id": "ABC123456",
        "insurance_company": "Blue Cross Blue Shield"
    }
    """
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['patient_name', 'patient_dob', 'member_id']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Perform LLM-powered verification
        verification_result = insurance_engine.verify_insurance_llm(
            patient_name=data['patient_name'],
            patient_dob=data['patient_dob'],
            member_id=data['member_id'],
            insurance_company=data.get('insurance_company')
        )
        
        return jsonify({
            'success': verification_result.get('verified', False),
            'verification_result': verification_result,
            'timestamp': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Insurance verification failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/insurance/companies', methods=['GET'])
@token_required
def get_insurance_companies(current_user):
    """Get list of supported insurance companies"""
    
    try:
        country = request.args.get('country', 'US')
        
        companies = insurance_engine.get_supported_insurance_companies(country=country)
        
        return jsonify({
            'count': len(companies),
            'companies': companies,
            'country': country
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to get insurance companies: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/insurance/companies', methods=['POST'])
@token_required
def add_insurance_company(current_user):
    """
    Add new insurance company to registry
    
    Request body:
    {
        "company_name": "New Insurance Co",
        "country": "KE",
        "website": "https://insurance.example.com",
        "verification_method": "web_scraping"
    }
    """
    
    try:
        data = request.get_json()
        
        result = insurance_engine.add_insurance_company(
            company_name=data['company_name'],
            country=data.get('country', 'US'),
            website=data.get('website'),
            verification_method=data.get('verification_method', 'web_scraping')
        )
        
        return jsonify({
            'success': result.get('success', False),
            'company_id': result.get('company_id'),
            'message': result.get('message')
        }), 201 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"Failed to add insurance company: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/insurance/extract-benefits', methods=['POST'])
@token_required
def extract_benefits(current_user):
    """
    Extract benefits from insurance document (PDF/image)
    
    Multipart form data:
    - file: PDF or image file
    - insurance_company: Name of insurance company (optional)
    """
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        insurance_company = request.form.get('insurance_company')
        
        # Save file temporarily
        temp_path = f"/tmp/{file.filename}"
        file.save(temp_path)
        
        # Extract benefits
        result = insurance_engine.extract_benefits_from_document(
            document_path=temp_path,
            insurance_company=insurance_company
        )
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return jsonify({
            'success': result.get('verified', False),
            'benefits': result,
            'confidence': result.get('confidence', 0)
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to extract benefits: {e}")
        return jsonify({'error': str(e)}), 500

# =====================================================
# CLAIMS MANAGEMENT ENDPOINTS
# =====================================================

@app.route('/api/claims', methods=['POST'])
@token_required
def create_claim(current_user):
    """
    Create new medical claim
    
    Request body:
    {
        "patient_id": 123,
        "service_date": "2024-01-15",
        "service_description": "Emergency Room Visit",
        "diagnosis_codes": ["ICD-10-CODE1"],
        "procedure_codes": ["CPT-CODE1"],
        "total_charge": 5000.00
    }
    """
    
    try:
        data = request.get_json()
        
        claim_result = claims_engine.create_claim(
            patient_id=data['patient_id'],
            service_date=data['service_date'],
            service_description=data.get('service_description'),
            diagnosis_codes=data.get('diagnosis_codes', []),
            procedure_codes=data.get('procedure_codes', []),
            total_charge=data['total_charge']
        )
        
        if claim_result.get('success'):
            # Calculate revenue
            revenue = revenue_optimizer.calculate_claim_revenue(claim_result['claim_id'])
            
            # Store revenue tracking
            revenue_optimizer.store_revenue_tracking(
                claim_id=claim_result['claim_id'],
                billing_month=data['service_date'][:7],
                total_charge=data['total_charge'],
                insurance_payment=revenue.get('insurance_payment', 0),
                patient_responsibility=revenue.get('patient_responsibility', 0),
                gotg_share=revenue.get('gotg_revenue_total', 0)
            )
        
        return jsonify(claim_result), 201 if claim_result.get('success') else 400
    
    except Exception as e:
        logger.error(f"Failed to create claim: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/claims/<int:claim_id>', methods=['GET'])
@token_required
def get_claim(current_user, claim_id):
    """Get claim details"""
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM claims WHERE id = ?", (claim_id,))
        claim = cursor.fetchone()
        conn.close()
        
        if not claim:
            return jsonify({'error': 'Claim not found'}), 404
        
        return jsonify({
            'id': claim['id'],
            'claim_id': claim['claim_id'],
            'patient_id': claim['patient_id'],
            'service_date': claim['service_date'],
            'total_charge': float(claim['total_charge']),
            'insurance_payment_estimate': float(claim['insurance_payment_estimate'] or 0),
            'patient_responsibility': float(claim['patient_responsibility'] or 0),
            'claim_status': claim['claim_status'],
            'created_at': claim['created_at'],
            'submitted_at': claim['submitted_at']
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to get claim: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/claims/<int:claim_id>/submit', methods=['POST'])
@token_required
def submit_claim(current_user, claim_id):
    """
    Submit claim to insurance company
    
    Request body (optional):
    {
        "submission_method": "web_portal|email|api|offline"
    }
    """
    
    try:
        data = request.get_json() or {}
        preferred_method = data.get('submission_method')
        
        result = claims_engine.submit_claim(
            claim_id=claim_id,
            preferred_submission_method=preferred_method
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"Failed to submit claim: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/claims/offline-queue', methods=['GET'])
@token_required
def get_offline_queue(current_user):
    """Get claims pending offline submission"""
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM offline_claim_queue
            WHERE submitted = 0
            ORDER BY created_at DESC
        """)
        
        queued_claims = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'count': len(queued_claims),
            'queued_claims': [dict(row) for row in queued_claims]
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to get offline queue: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/claims/sync-offline', methods=['POST'])
@token_required
def sync_offline_claims(current_user):
    """Sync queued offline claims when connectivity available"""
    
    try:
        result = claims_engine.sync_offline_claims()
        
        return jsonify({
            'success': True,
            'synced_count': result.get('synced_count', 0),
            'failed_count': result.get('failed_count', 0),
            'timestamp': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Offline sync failed: {e}")
        return jsonify({'error': str(e)}), 500

# =====================================================
# REVENUE TRACKING ENDPOINTS
# =====================================================

@app.route('/api/revenue/monthly/<int:year>/<int:month>', methods=['GET'])
@token_required
def get_monthly_revenue(current_user, year, month):
    """Get monthly revenue summary for sustainability reporting"""
    
    try:
        summary = revenue_optimizer.calculate_monthly_revenue_summary(year, month)
        
        return jsonify(summary), 200 if 'error' not in summary else 400
    
    except Exception as e:
        logger.error(f"Failed to get monthly revenue: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/revenue/portfolio', methods=['GET'])
@token_required
def get_portfolio_revenue(current_user):
    """
    Get portfolio revenue summary
    
    Query parameters:
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    """
    
    try:
        start_date = request.args.get('start_date', '2024-01-01')
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        portfolio = revenue_optimizer.calculate_portfolio_revenue(start_date, end_date)
        
        return jsonify(portfolio), 200 if 'error' not in portfolio else 400
    
    except Exception as e:
        logger.error(f"Failed to get portfolio revenue: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/revenue/projection', methods=['GET'])
@token_required
def revenue_projection(current_user):
    """Get revenue projection for next 3 years"""
    
    try:
        years = int(request.args.get('years', 3))
        
        projection = revenue_optimizer.project_annual_revenue(years)
        
        return jsonify(projection), 200 if 'error' not in projection else 400
    
    except Exception as e:
        logger.error(f"Failed to project revenue: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/revenue/sustainability-forecast', methods=['GET'])
@token_required
def sustainability_forecast(current_user):
    """Forecast when billing will sustain GOTG operations"""
    
    try:
        forecast = revenue_optimizer.forecast_sustainability_timeline()
        
        return jsonify(forecast), 200 if 'error' not in forecast else 400
    
    except Exception as e:
        logger.error(f"Failed to forecast sustainability: {e}")
        return jsonify({'error': str(e)}), 500

# =====================================================
# DATA SYNC ENDPOINTS
# =====================================================

@app.route('/api/sync/pull-ris/<patient_id>', methods=['POST'])
@token_required
def pull_ris_data(current_user, patient_id):
    """Pull patient data from RIS module"""
    
    try:
        result = sync_manager.pull_patient_data_from_ris(patient_id)
        
        return jsonify(result), 200 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"RIS sync failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/pull-procedures/<patient_id>', methods=['POST'])
@token_required
def pull_procedures(current_user, patient_id):
    """Pull procedure/diagnosis data from Dictation module"""
    
    try:
        result = sync_manager.pull_procedures_from_dictation(patient_id)
        
        return jsonify(result), 200 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"Dictation sync failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/pull-imaging/<patient_id>', methods=['POST'])
@token_required
def pull_imaging(current_user, patient_id):
    """Pull imaging data from PACS module"""
    
    try:
        result = sync_manager.pull_imaging_from_pacs(patient_id)
        
        return jsonify(result), 200 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"PACS sync failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/offline-queue', methods=['POST'])
@token_required
def process_sync_queue(current_user):
    """Process queued syncs when connectivity available"""
    
    try:
        result = sync_manager.process_offline_sync_queue()
        
        return jsonify({
            'success': 'error' not in result,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Sync queue processing failed: {e}")
        return jsonify({'error': str(e)}), 500

# =====================================================
# ADMINISTRATIVE ENDPOINTS
# =====================================================

@app.route('/api/admin/optimization-recommendations', methods=['GET'])
@token_required
def get_optimization_recommendations(current_user):
    """Get AI-powered optimization recommendations"""
    
    try:
        recommendations = revenue_optimizer.recommend_allocation_optimization()
        
        return jsonify(recommendations), 200 if 'error' not in recommendations else 400
    
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
@token_required
def get_module_stats(current_user):
    """Get module statistics"""
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get stats
        cursor.execute("SELECT COUNT(*) FROM claims")
        claim_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM offline_claim_queue WHERE submitted = 0")
        pending_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT SUM(gift_of_givers_share) FROM revenue_tracking
        """)
        total_revenue = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'total_claims': claim_count,
            'pending_offline': pending_count,
            'total_gotg_revenue': float(total_revenue),
            'timestamp': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return jsonify({'error': str(e)}), 500

# =====================================================
# ERROR HANDLING
# =====================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# =====================================================
# STARTUP
# =====================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    debug = os.environ.get('DEBUG', 'False') == 'True'
    
    logger.info(f"Starting Medical-Billing-4 Flask API on port {port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )

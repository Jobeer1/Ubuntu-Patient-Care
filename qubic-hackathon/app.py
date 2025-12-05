"""
QUBIC - Quantified Ubuntu Contribution Integrity Crucible
Flask Backend API for Hackathon Demo

Provides REST API endpoints for:
- Leaderboard ranking and filtering
- AI-powered scoring simulation
- DAO governance data
- Analytics and statistics
- Real-time updates
"""

from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import random
import os
from typing import Dict, List, Tuple

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')

# Enable CORS with proper configuration for localhost and IP access
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:*", "http://127.0.0.1:*", "http://155.235.81.53:*"],
        "methods": ["GET", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# ============================================================================
# DATA MODELS & CONSTANTS
# ============================================================================

CONTRIBUTION_MODULES = [
    "PACS Module", "RIS Module", "Dictation/Reporting",
    "Medical Billing", "Security/Compliance", "AI/ML Models"
]

SCORE_WEIGHTS = {
    "code_quality": 0.30,
    "healthcare_impact": 0.25,
    "documentation": 0.20,
    "innovation": 0.15,
    "integration": 0.10
}

TIERS = {
    "platinum": {"range": (90, 100), "votes": 5, "icon": "🏆"},
    "gold": {"range": (80, 89), "votes": 3, "icon": "🥇"},
    "silver": {"range": (70, 79), "votes": 2, "icon": "🥈"},
    "bronze": {"range": (60, 69), "votes": 1, "icon": "🥉"},
    "recognized": {"range": (50, 59), "votes": 1, "icon": "⭐"}
}

MODULE_BONUSES = {
    "PACS Module": 5,
    "RIS Module": 5,
    "Dictation/Reporting": 4,
    "Medical Billing": 3,
    "Cross-Module Integration": 7,
    "Security/Compliance": 6,
    "AI/ML Models": 5
}

# ============================================================================
# MOCK DATA GENERATION
# ============================================================================

class ContributionGenerator:
    """Generate realistic mock contributor and contribution data"""
    
    FIRST_NAMES = [
        "Dr. Sarah", "James", "Maria", "Ahmed", "Lisa", "Carlos",
        "Yuki", "Sophie", "Marcus", "Priya", "Elena", "David",
        "Nina", "Rajesh", "Anna", "Michael", "Fatima", "Zhang"
    ]
    
    LAST_NAMES = [
        "Chen", "Mitchell", "Rodriguez", "Hassan", "Park", "Espinoza",
        "Tanaka", "Laurent", "Johnson", "Patel", "Rossi", "Williams",
        "Kim", "Kumar", "Silva", "Brown", "Ahmed", "Liu"
    ]
    
    CONTRIBUTIONS = [
        "Advanced PACS Module Development with AI-Powered Image Analysis",
        "RIS Module Enhancement and Patient Management System Integration",
        "Comprehensive Documentation Suite and Clinical Workflow Guides",
        "Medical Billing System Integration and Revenue Cycle Optimization",
        "Security Audit and HIPAA/POPIA Compliance Enhancement",
        "AI/ML Model Development for Clinical Decision Support",
        "Cross-Module Integration Framework Implementation",
        "Performance Optimization and Database Scaling",
        "Mobile App Development for Patient Portal",
        "API Documentation and Developer Tools",
        "Testing Framework and Quality Assurance System",
        "DevOps Pipeline and CI/CD Implementation"
    ]
    
    @staticmethod
    def generate_contributor(index: int) -> Dict:
        """Generate a single contributor"""
        first = ContributionGenerator.FIRST_NAMES[index % len(ContributionGenerator.FIRST_NAMES)]
        last = ContributionGenerator.LAST_NAMES[(index + 3) % len(ContributionGenerator.LAST_NAMES)]
        
        # Generate realistic score
        base_score = random.gauss(75, 10)
        score = max(50, min(100, int(base_score)))
        
        # Determine tier
        tier = next((t for t, r in TIERS.items() if r["range"][0] <= score <= r["range"][1]), "recognized")
        
        # Generate score breakdown
        breakdown = {
            "code_quality": max(0, min(30, int(score * SCORE_WEIGHTS["code_quality"] + random.uniform(-5, 5)))),
            "healthcare_impact": max(0, min(25, int(score * SCORE_WEIGHTS["healthcare_impact"] + random.uniform(-4, 4)))),
            "documentation": max(0, min(20, int(score * SCORE_WEIGHTS["documentation"] + random.uniform(-3, 3)))),
            "innovation": max(0, min(15, int(score * SCORE_WEIGHTS["innovation"] + random.uniform(-2, 2)))),
            "integration": max(0, min(10, int(score * SCORE_WEIGHTS["integration"] + random.uniform(-2, 2))))
        }
        
        module = random.choice(CONTRIBUTION_MODULES)
        contribution_count = random.randint(5, 50)
        
        return {
            "id": f"user_{index}",
            "name": f"{first} {last}",
            "github": f"{first.lower()}{last.lower()}".replace(" ", ""),
            "score": score,
            "tier": tier,
            "module": module,
            "contributions": contribution_count,
            "breakdown": breakdown,
            "joined": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
            "avatar": f"https://i.pravatar.cc/150?img={index}",
            "rank": index + 1
        }
    
    @staticmethod
    def generate_leaderboard(count: int = 156) -> List[Dict]:
        """Generate full leaderboard with real contributions first, then random contributors"""
        # Real scored contributions (from QUBIC assessment)
        real_contributions = [
            {
                "id": "contrib_ai_teleradiology",
                "name": "AI Teleradiology Dashboard",
                "github": "ubuntu-patient-care/ai-teleradiology",
                "score": 92,
                "tier": "platinum",
                "module": "PACS Module",
                "contributions": 78,
                "avatar": "https://i.pravatar.cc/150?img=42",
                "rank": 1,
                "breakdown": {"code_quality": 28, "healthcare_impact": 29, "documentation": 30, "innovation": 27, "integration": 28},
                "joined": (datetime.now() - timedelta(days=180)).isoformat(),
                "url": "https://github.com/Jobeer1/Ubuntu-Patient-Care/tree/main/specs/ai-teleradiology"
            },
            {
                "id": "contrib_gotg_version",
                "name": "GOTG Battle-Ready Edition",
                "github": "ubuntu-patient-care/gotg",
                "score": 89,
                "tier": "gold",
                "module": "Humanitarian System",
                "contributions": 72,
                "avatar": "https://i.pravatar.cc/150?img=88",
                "rank": 2,
                "breakdown": {"code_quality": 28, "healthcare_impact": 29, "documentation": 29, "innovation": 28, "integration": 28},
                "joined": (datetime.now() - timedelta(days=150)).isoformat(),
                "url": "https://github.com/Jobeer1/Ubuntu-Patient-Care/tree/main/GOTG_version"
            },
            {
                "id": "contrib_cloud_orchestration",
                "name": "Cloud Orchestration AI Engine",
                "github": "ubuntu-patient-care/cloud-orchestration",
                "score": 87,
                "tier": "gold",
                "module": "Enterprise Automation",
                "contributions": 68,
                "avatar": "https://i.pravatar.cc/150?img=77",
                "rank": 3,
                "breakdown": {"code_quality": 26, "healthcare_impact": 28, "documentation": 27, "innovation": 26, "integration": 25},
                "joined": (datetime.now() - timedelta(days=120)).isoformat(),
                "url": "https://github.com/Jobeer1/Ubuntu-Patient-Care/tree/main/cloud_orchestration"
            },
            {
                "id": "contrib_ibm_hackathon",
                "name": "IBM Hackathon Submission",
                "github": "ubuntu-patient-care/ibm-hackathon",
                "score": 88,
                "tier": "gold",
                "module": "Enterprise System",
                "contributions": 65,
                "avatar": "https://i.pravatar.cc/150?img=99",
                "rank": 4,
                "breakdown": {"code_quality": 27, "healthcare_impact": 26, "documentation": 27, "innovation": 26, "integration": 27},
                "joined": (datetime.now() - timedelta(days=100)).isoformat(),
                "url": "https://github.com/Jobeer1/Ubuntu-Patient-Care/tree/main/IBM-HACKATHON-SUBMISSION"
            }
        ]
        
        # Generate additional random contributors to reach target count
        random_contributors = [ContributionGenerator.generate_contributor(i) for i in range(4, count)]
        random_contributors.sort(key=lambda x: x["score"], reverse=True)
        
        # Combine and update ranks
        contributors = real_contributions + random_contributors
        for i, c in enumerate(contributors):
            c["rank"] = i + 1
        return contributors

LEADERBOARD = ContributionGenerator.generate_leaderboard()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_statistics():
    """Calculate leaderboard statistics"""
    return {
        "total_contributors": len(LEADERBOARD),
        "total_contributions": sum(c["contributions"] for c in LEADERBOARD),
        "monthly_rewards": 30,
        "tokens_distributed": sum(c["score"] // 20 for c in LEADERBOARD if c["score"] >= 60),
        "average_score": round(sum(c["score"] for c in LEADERBOARD) / len(LEADERBOARD), 2),
        "tier_distribution": {
            tier: len([c for c in LEADERBOARD if c["tier"] == tier])
            for tier in TIERS.keys()
        }
    }

def get_tier_info(tier: str) -> Dict:
    """Get tier information"""
    return {
        "tier": tier,
        "range": TIERS[tier]["range"],
        "icon": TIERS[tier]["icon"],
        "voting_power": TIERS[tier]["votes"]
    }

def simulate_ai_scoring() -> Dict:
    """Simulate AI-powered scoring evaluation"""
    return {
        "timestamp": datetime.now().isoformat(),
        "model": "Gemini Flash 2.0",
        "status": "completed",
        "evaluation_time_ms": random.randint(500, 2000),
        "confidence": round(random.uniform(0.85, 0.99), 3),
        "criteria_evaluated": 5,
        "factors": {
            "code_quality": random.uniform(0.8, 0.95),
            "healthcare_impact": random.uniform(0.8, 0.95),
            "documentation": random.uniform(0.75, 0.95),
            "innovation": random.uniform(0.7, 0.95),
            "integration": random.uniform(0.75, 0.95)
        }
    }

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/')
def index():
    """Serve main application"""
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/api')
def api_root():
    return jsonify({
        "name": "QUBIC API",
        "version": "1.0.0",
        "description": "Blockchain Healthcare Contribution DAO",
        "endpoints": {
            "leaderboard": "/api/leaderboard",
            "contributor": "/api/contributor/<id>",
            "statistics": "/api/statistics",
            "scoring": "/api/scoring",
            "dao": "/api/dao",
            "tiers": "/api/tiers"
        }
    })

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard with optional filtering"""
    tier = request.args.get('tier', None)
    limit = int(request.args.get('limit', 50))
    page = int(request.args.get('page', 1))
    
    # Filter by tier if specified
    filtered = LEADERBOARD
    if tier and tier in TIERS:
        filtered = [c for c in LEADERBOARD if c["tier"] == tier]
    
    # Pagination
    start = (page - 1) * limit
    end = start + limit
    
    return jsonify({
        "status": "success",
        "total": len(filtered),
        "page": page,
        "limit": limit,
        "data": filtered[start:end]
    })

@app.route('/api/leaderboard/top', methods=['GET'])
def get_top_contributors():
    """Get top contributors for current month"""
    limit = int(request.args.get('limit', 10))
    return jsonify({
        "status": "success",
        "period": "current_month",
        "data": [
            {
                **LEADERBOARD[0],
                "reward": "15 UC",
                "percentage": "50%"
            },
            {
                **LEADERBOARD[1],
                "reward": "9 UC",
                "percentage": "30%"
            },
            {
                **LEADERBOARD[2],
                "reward": "6 UC",
                "percentage": "20%"
            }
        ]
    })

@app.route('/api/contributor/<contributor_id>', methods=['GET'])
def get_contributor(contributor_id):
    """Get detailed contributor information"""
    contributor = next((c for c in LEADERBOARD if c["id"] == contributor_id), None)
    
    if not contributor:
        return jsonify({"error": "Contributor not found"}), 404
    
    # Add additional detailed information
    contributor_detail = {
        **contributor,
        "voting_power": TIERS[contributor["tier"]]["votes"],
        "governance_eligible": contributor["score"] >= 50,
        "monthly_rewards_history": [
            {"month": "November", "reward": "0 UC", "rank": "N/A"},
            {"month": "October", "reward": "6 UC", "rank": "3rd"},
            {"month": "September", "reward": "9 UC", "rank": "2nd"}
        ],
        "contribution_timeline": [
            {
                "date": (datetime.now() - timedelta(days=i)).isoformat(),
                "type": random.choice(["feature", "bugfix", "docs", "test"]),
                "impact": random.randint(50, 100)
            }
            for i in range(10)
        ]
    }
    
    return jsonify({
        "status": "success",
        "data": contributor_detail
    })

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get overall statistics"""
    stats = calculate_statistics()
    
    return jsonify({
        "status": "success",
        "data": stats,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/scoring', methods=['GET'])
def get_scoring_info():
    """Get scoring framework information"""
    return jsonify({
        "status": "success",
        "framework": {
            "dimensions": [
                {
                    "name": "Code Quality",
                    "weight": 0.30,
                    "max_points": 30,
                    "description": "Technical excellence, best practices"
                },
                {
                    "name": "Healthcare Impact",
                    "weight": 0.25,
                    "max_points": 25,
                    "description": "Direct benefit to patient care"
                },
                {
                    "name": "Documentation",
                    "weight": 0.20,
                    "max_points": 20,
                    "description": "Clarity and completeness of docs"
                },
                {
                    "name": "Innovation",
                    "weight": 0.15,
                    "max_points": 15,
                    "description": "Novel approaches and creativity"
                },
                {
                    "name": "Integration",
                    "weight": 0.10,
                    "max_points": 10,
                    "description": "System integration quality"
                }
            ],
            "module_bonuses": MODULE_BONUSES,
            "ai_evaluation": simulate_ai_scoring()
        }
    })

@app.route('/api/tiers', methods=['GET'])
def get_tiers():
    """Get tier information"""
    tier_list = []
    for tier_name, tier_data in TIERS.items():
        tier_list.append({
            "name": tier_name.capitalize(),
            "icon": tier_data["icon"],
            "range": f"{tier_data['range'][0]}-{tier_data['range'][1]}",
            "voting_power": tier_data["votes"],
            "contributors": len([c for c in LEADERBOARD if c["tier"] == tier_name])
        })
    
    return jsonify({
        "status": "success",
        "data": tier_list
    })

@app.route('/api/dao', methods=['GET'])
def get_dao_info():
    """Get DAO governance information"""
    total_tokens = 1000
    monthly_pool = 30
    
    return jsonify({
        "status": "success",
        "data": {
            "total_tokens": total_tokens,
            "token_name": "UC",
            "monthly_pool": monthly_pool,
            "treasury": {
                "monthly_rewards": monthly_pool,
                "development_fund": 300,
                "emergency_reserve": 200,
                "future_growth": total_tokens - monthly_pool - 300 - 200
            },
            "voting_system": {
                "voting_power_by_tier": {tier: data["votes"] for tier, data in TIERS.items()},
                "governance_types": [
                    {
                        "type": "Tactical",
                        "approval_threshold": 51,
                        "quorum": 20,
                        "examples": ["Rubric adjustments", "Module bonuses"]
                    },
                    {
                        "type": "Strategic",
                        "approval_threshold": 66,
                        "quorum": 40,
                        "examples": ["Weight changes", "Treasury allocation"]
                    },
                    {
                        "type": "Critical",
                        "approval_threshold": 80,
                        "quorum": 60,
                        "examples": ["Mission changes", "Dissolution"]
                    }
                ]
            },
            "active_proposals": 3,
            "total_voted": len([c for c in LEADERBOARD if c["score"] >= 50])
        }
    })

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get analytics data"""
    return jsonify({
        "status": "success",
        "data": {
            "monthly_contributions": [
                {"month": "September", "count": 450},
                {"month": "October", "count": 520},
                {"month": "November", "count": 680},
                {"month": "December", "count": 845}
            ],
            "score_distribution": {
                "50-60": 5,
                "60-70": 12,
                "70-80": 28,
                "80-90": 35,
                "90-100": 15
            },
            "module_breakdown": {
                module: len([c for c in LEADERBOARD if c["module"] == module])
                for module in CONTRIBUTION_MODULES
            },
            "blockchain_transactions": {
                "total": 156,
                "successful": 154,
                "pending": 2,
                "failed": 0
            }
        }
    })

@app.route('/api/search', methods=['GET'])
def search():
    """Search contributors"""
    query = request.args.get('q', '').lower()
    
    if not query:
        return jsonify({"error": "Query parameter 'q' required"}), 400
    
    results = [
        c for c in LEADERBOARD
        if query in c["name"].lower() or query in c["github"].lower()
    ]
    
    return jsonify({
        "status": "success",
        "query": query,
        "results": len(results),
        "data": results[:20]
    })

@app.route('/api/export', methods=['GET'])
def export_data():
    """Export leaderboard data"""
    format_type = request.args.get('format', 'json')
    
    if format_type == 'csv':
        # Return CSV format
        csv_lines = [
            "Rank,Name,GitHub,Score,Tier,Module,Contributions"
        ]
        for c in LEADERBOARD:
            csv_lines.append(
                f"{c['rank']},{c['name']},{c['github']},{c['score']},{c['tier']},{c['module']},{c['contributions']}"
            )
        return '\n'.join(csv_lines), 200, {'Content-Type': 'text/csv'}
    
    # Default JSON format
    return jsonify({
        "status": "success",
        "format": "json",
        "exported_at": datetime.now().isoformat(),
        "data": LEADERBOARD
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "contributors_loaded": len(LEADERBOARD),
        "api_version": "1.0.0"
    })

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

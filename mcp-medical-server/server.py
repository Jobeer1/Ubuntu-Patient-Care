#!/usr/bin/env python3
"""
MCP Server for Medical Scheme Authorizations
Solves: Pre-authorization requests, benefits calculations, offline validation
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Initialize MCP Server
app = Server("ubuntu-patient-care-medical-auth")

# Database connection
DB_PATH = "medical_schemes.db"

def init_database():
    """Initialize offline medical schemes database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Medical aid members table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medical_aid_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_code TEXT NOT NULL,
            member_number TEXT NOT NULL,
            id_number TEXT NOT NULL,
            surname TEXT NOT NULL,
            first_names TEXT NOT NULL,
            date_of_birth DATE NOT NULL,
            plan_code TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            effective_date DATE,
            termination_date DATE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(scheme_code, member_number)
        )
    """)
    
    # Benefits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheme_benefits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_code TEXT NOT NULL,
            plan_code TEXT NOT NULL,
            nrpl_code TEXT NOT NULL,
            procedure_name TEXT NOT NULL,
            benefit_amount DECIMAL(10,2) NOT NULL,
            co_payment_percentage DECIMAL(5,2) DEFAULT 0,
            annual_limit DECIMAL(12,2),
            per_procedure_limit DECIMAL(10,2),
            pre_auth_required BOOLEAN DEFAULT 0,
            typical_turnaround_hours INTEGER DEFAULT 4,
            approval_rate DECIMAL(5,2) DEFAULT 0.95,
            exclusions TEXT,
            effective_date DATE,
            expiry_date DATE,
            UNIQUE(scheme_code, plan_code, nrpl_code)
        )
    """)
    
    # Pre-authorization requests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preauth_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preauth_id TEXT UNIQUE NOT NULL,
            patient_id TEXT NOT NULL,
            member_number TEXT NOT NULL,
            scheme_code TEXT NOT NULL,
            procedure_code TEXT NOT NULL,
            clinical_indication TEXT NOT NULL,
            icd10_codes TEXT,
            urgency TEXT DEFAULT 'routine',
            status TEXT DEFAULT 'queued',
            approval_probability DECIMAL(5,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP,
            approved_at TIMESTAMP,
            auth_number TEXT,
            valid_until DATE,
            rejection_reason TEXT
        )
    """)
    
    # Member utilization table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS member_utilization (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_number TEXT NOT NULL,
            scheme_code TEXT NOT NULL,
            year INTEGER NOT NULL,
            nrpl_code TEXT NOT NULL,
            amount_used DECIMAL(12,2) DEFAULT 0,
            claims_count INTEGER DEFAULT 0,
            last_claim_date DATE,
            UNIQUE(member_number, year, nrpl_code)
        )
    """)
    
    conn.commit()
    
    # Insert sample data for testing
    insert_sample_data(cursor)
    conn.commit()
    conn.close()

def insert_sample_data(cursor):
    """Insert sample medical scheme data for testing"""
    
    # Sample members
    members = [
        ('DISCOVERY', '1234567890', '8001015009087', 'SMITH', 'JOHN', '1980-01-01', 'EXECUTIVE', 'Executive Plan', 'active'),
        ('MOMENTUM', '87654321', '8505125009088', 'JONES', 'MARY', '1985-05-12', 'CUSTOM', 'Custom Plan', 'active'),
        ('BONITAS', 'BN12345678', '9203156009089', 'BROWN', 'DAVID', '1992-03-15', 'STANDARD', 'Standard Plan', 'active'),
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO medical_aid_members 
        (scheme_code, member_number, id_number, surname, first_names, date_of_birth, plan_code, plan_name, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, members)
    
    # Sample benefits (South African NRPL codes)
    benefits = [
        # CT Scans
        ('DISCOVERY', 'EXECUTIVE', '3011', 'CT Head without contrast', 1850.00, 10, 50000, 5000, 1, 4, 0.95),
        ('DISCOVERY', 'EXECUTIVE', '3012', 'CT Head with contrast', 2450.00, 10, 50000, 5000, 1, 4, 0.93),
        ('DISCOVERY', 'EXECUTIVE', '3021', 'CT Chest', 2100.00, 10, 50000, 5000, 1, 4, 0.94),
        ('MOMENTUM', 'CUSTOM', '3011', 'CT Head without contrast', 1750.00, 15, 40000, 4000, 1, 6, 0.92),
        ('BONITAS', 'STANDARD', '3011', 'CT Head without contrast', 1650.00, 20, 30000, 3000, 1, 8, 0.90),
        
        # MRI Scans
        ('DISCOVERY', 'EXECUTIVE', '3111', 'MRI Brain without contrast', 3500.00, 10, 50000, 8000, 1, 6, 0.94),
        ('DISCOVERY', 'EXECUTIVE', '3112', 'MRI Brain with contrast', 4200.00, 10, 50000, 8000, 1, 6, 0.92),
        
        # X-Rays (no pre-auth)
        ('DISCOVERY', 'EXECUTIVE', '2001', 'X-Ray Chest PA', 350.00, 0, 10000, 1000, 0, 0, 0.99),
        ('DISCOVERY', 'EXECUTIVE', '2011', 'X-Ray Skull', 450.00, 0, 10000, 1000, 0, 0, 0.99),
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO scheme_benefits 
        (scheme_code, plan_code, nrpl_code, procedure_name, benefit_amount, co_payment_percentage, 
         annual_limit, per_procedure_limit, pre_auth_required, typical_turnaround_hours, approval_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, benefits)

# Initialize database on startup
init_database()

# MCP Tool Handlers

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available medical authorization tools"""
    return [
        Tool(
            name="validate_medical_aid",
            description="Validate medical aid member (works offline)",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_number": {"type": "string", "description": "Medical aid member number"},
                    "scheme_code": {"type": "string", "description": "Scheme code (e.g., DISCOVERY, MOMENTUM)"},
                    "id_number": {"type": "string", "description": "SA ID number (optional for validation)"}
                },
                "required": ["member_number", "scheme_code"]
            }
        ),
        Tool(
            name="validate_preauth_requirements",
            description="Check if procedure requires pre-authorization (offline)",
            inputSchema={
                "type": "object",
                "properties": {
                    "scheme_code": {"type": "string"},
                    "plan_code": {"type": "string"},
                    "procedure_code": {"type": "string", "description": "NRPL code"}
                },
                "required": ["scheme_code", "plan_code", "procedure_code"]
            }
        ),
        Tool(
            name="estimate_patient_cost",
            description="Calculate patient portion for procedure (offline)",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_number": {"type": "string"},
                    "scheme_code": {"type": "string"},
                    "procedure_code": {"type": "string", "description": "NRPL code"}
                },
                "required": ["member_number", "scheme_code", "procedure_code"]
            }
        ),
        Tool(
            name="create_preauth_request",
            description="Create pre-authorization request with validation",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "member_number": {"type": "string"},
                    "scheme_code": {"type": "string"},
                    "procedure_code": {"type": "string", "description": "NRPL code"},
                    "clinical_indication": {"type": "string"},
                    "icd10_codes": {"type": "array", "items": {"type": "string"}},
                    "urgency": {"type": "string", "enum": ["routine", "urgent", "emergency"], "default": "routine"}
                },
                "required": ["patient_id", "member_number", "scheme_code", "procedure_code", "clinical_indication"]
            }
        ),
        Tool(
            name="check_preauth_status",
            description="Check status of pre-authorization request",
            inputSchema={
                "type": "object",
                "properties": {
                    "preauth_id": {"type": "string", "description": "Pre-authorization ID"}
                },
                "required": ["preauth_id"]
            }
        ),
        Tool(
            name="list_pending_preauths",
            description="List all pending pre-authorization requests",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["queued", "submitted", "approved", "rejected"], "default": "queued"}
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    
    try:
        if name == "validate_medical_aid":
            result = validate_medical_aid(arguments)
        elif name == "validate_preauth_requirements":
            result = validate_preauth_requirements(arguments)
        elif name == "estimate_patient_cost":
            result = estimate_patient_cost(arguments)
        elif name == "create_preauth_request":
            result = create_preauth_request(arguments)
        elif name == "check_preauth_status":
            result = check_preauth_status(arguments)
        elif name == "list_pending_preauths":
            result = list_pending_preauths(arguments)
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]

def validate_medical_aid(args: Dict) -> Dict:
    """Validate medical aid member (offline)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM medical_aid_members 
        WHERE member_number = ? AND scheme_code = ?
    """, (args['member_number'], args['scheme_code']))
    
    member = cursor.fetchone()
    conn.close()
    
    if not member:
        return {
            "valid": False,
            "error": "Member not found",
            "suggestion": "Please verify member number and scheme code"
        }
    
    # Validate ID number if provided
    if 'id_number' in args and args['id_number']:
        if member[3] != args['id_number']:  # id_number column
            return {
                "valid": False,
                "error": "ID number mismatch",
                "expected": member[3],
                "provided": args['id_number']
            }
    
    return {
        "valid": True,
        "member": {
            "scheme_code": member[1],
            "member_number": member[2],
            "id_number": member[3],
            "full_name": f"{member[5]} {member[4]}",  # first_names surname
            "date_of_birth": member[6],
            "plan_code": member[7],
            "plan_name": member[8],
            "status": member[9]
        },
        "offline": True,
        "last_updated": member[12]
    }

def validate_preauth_requirements(args: Dict) -> Dict:
    """Check if procedure requires pre-authorization (offline)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM scheme_benefits 
        WHERE scheme_code = ? AND plan_code = ? AND nrpl_code = ?
    """, (args['scheme_code'], args['plan_code'], args['procedure_code']))
    
    benefit = cursor.fetchone()
    conn.close()
    
    if not benefit:
        return {
            "error": "Benefit not found for this scheme/plan/procedure combination",
            "requires_online_check": True
        }
    
    return {
        "requires_preauth": bool(benefit[9]),  # pre_auth_required
        "procedure_name": benefit[4],
        "benefit_amount": float(benefit[5]),
        "co_payment_percentage": float(benefit[6]),
        "typical_turnaround": f"{benefit[10]} hours",
        "approval_rate": float(benefit[11]),
        "required_documents": [
            "Clinical indication",
            "ICD-10 diagnosis codes",
            "Referring doctor details"
        ] if benefit[9] else [],
        "offline": True
    }

def estimate_patient_cost(args: Dict) -> Dict:
    """Calculate patient portion for procedure (offline)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get member details
    cursor.execute("""
        SELECT plan_code FROM medical_aid_members 
        WHERE member_number = ? AND scheme_code = ?
    """, (args['member_number'], args['scheme_code']))
    
    member = cursor.fetchone()
    if not member:
        conn.close()
        return {"error": "Member not found"}
    
    plan_code = member[0]
    
    # Get benefit details
    cursor.execute("""
        SELECT * FROM scheme_benefits 
        WHERE scheme_code = ? AND plan_code = ? AND nrpl_code = ?
    """, (args['scheme_code'], plan_code, args['procedure_code']))
    
    benefit = cursor.fetchone()
    if not benefit:
        conn.close()
        return {"error": "Benefit not found"}
    
    # Get utilization
    current_year = datetime.now().year
    cursor.execute("""
        SELECT amount_used FROM member_utilization 
        WHERE member_number = ? AND year = ? AND nrpl_code = ?
    """, (args['member_number'], current_year, args['procedure_code']))
    
    utilization = cursor.fetchone()
    used_amount = float(utilization[0]) if utilization else 0.0
    
    conn.close()
    
    # Calculate costs
    procedure_cost = float(benefit[5])
    co_payment_percentage = float(benefit[6])
    annual_limit = float(benefit[7]) if benefit[7] else 999999.0
    
    co_payment = procedure_cost * (co_payment_percentage / 100)
    available_benefit = annual_limit - used_amount
    medical_aid_portion = min(procedure_cost - co_payment, available_benefit)
    patient_portion = procedure_cost - medical_aid_portion
    
    return {
        "procedure_name": benefit[4],
        "procedure_cost": round(procedure_cost, 2),
        "medical_aid_portion": round(medical_aid_portion, 2),
        "patient_portion": round(patient_portion, 2),
        "co_payment": round(co_payment, 2),
        "co_payment_percentage": co_payment_percentage,
        "annual_limit": round(annual_limit, 2),
        "used_this_year": round(used_amount, 2),
        "remaining_benefit": round(available_benefit, 2),
        "preauth_required": bool(benefit[9]),
        "confidence": "high",
        "offline": True,
        "currency": "ZAR"
    }

def create_preauth_request(args: Dict) -> Dict:
    """Create pre-authorization request with validation"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Validate member
    cursor.execute("""
        SELECT plan_code FROM medical_aid_members 
        WHERE member_number = ? AND scheme_code = ?
    """, (args['member_number'], args['scheme_code']))
    
    member = cursor.fetchone()
    if not member:
        conn.close()
        return {"error": "Invalid member number or scheme code"}
    
    plan_code = member[0]
    
    # Check if pre-auth required
    cursor.execute("""
        SELECT pre_auth_required, approval_rate, typical_turnaround_hours 
        FROM scheme_benefits 
        WHERE scheme_code = ? AND plan_code = ? AND nrpl_code = ?
    """, (args['scheme_code'], plan_code, args['procedure_code']))
    
    benefit = cursor.fetchone()
    if not benefit:
        conn.close()
        return {"error": "Procedure not covered by this plan"}
    
    if not benefit[0]:
        conn.close()
        return {
            "preauth_required": False,
            "message": "This procedure does not require pre-authorization",
            "can_proceed": True
        }
    
    # Generate pre-auth ID
    preauth_id = f"PA-{datetime.now().strftime('%Y%m%d')}-{args['patient_id'][:6]}"
    
    # Insert pre-auth request
    icd10_codes_str = json.dumps(args.get('icd10_codes', []))
    
    cursor.execute("""
        INSERT INTO preauth_requests 
        (preauth_id, patient_id, member_number, scheme_code, procedure_code, 
         clinical_indication, icd10_codes, urgency, status, approval_probability)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?)
    """, (
        preauth_id,
        args['patient_id'],
        args['member_number'],
        args['scheme_code'],
        args['procedure_code'],
        args['clinical_indication'],
        icd10_codes_str,
        args.get('urgency', 'routine'),
        benefit[1]  # approval_rate
    ))
    
    conn.commit()
    conn.close()
    
    estimated_hours = benefit[2]
    estimated_completion = datetime.now() + timedelta(hours=estimated_hours)
    
    return {
        "success": True,
        "preauth_id": preauth_id,
        "status": "queued_for_submission",
        "estimated_approval_time": f"{estimated_hours} hours",
        "estimated_completion": estimated_completion.isoformat(),
        "approval_probability": float(benefit[1]),
        "validation_passed": True,
        "missing_info": [],
        "next_steps": [
            "Pre-auth will be submitted automatically when online",
            "You will be notified when approved",
            f"Patient can proceed with scan if {args.get('urgency', 'routine')} == 'emergency'"
        ],
        "offline": True
    }

def check_preauth_status(args: Dict) -> Dict:
    """Check status of pre-authorization request"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM preauth_requests WHERE preauth_id = ?
    """, (args['preauth_id'],))
    
    request = cursor.fetchone()
    conn.close()
    
    if not request:
        return {"error": "Pre-authorization request not found"}
    
    return {
        "preauth_id": request[1],
        "patient_id": request[2],
        "status": request[9],
        "created_at": request[10],
        "submitted_at": request[11],
        "approved_at": request[12],
        "auth_number": request[13],
        "valid_until": request[14],
        "rejection_reason": request[15],
        "approval_probability": float(request[10]) if request[10] else None
    }

def list_pending_preauths(args: Dict) -> Dict:
    """List all pending pre-authorization requests"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    status = args.get('status', 'queued')
    
    cursor.execute("""
        SELECT preauth_id, patient_id, procedure_code, urgency, created_at, approval_probability
        FROM preauth_requests 
        WHERE status = ?
        ORDER BY created_at DESC
    """, (status,))
    
    requests = cursor.fetchall()
    conn.close()
    
    return {
        "status": status,
        "count": len(requests),
        "requests": [
            {
                "preauth_id": r[0],
                "patient_id": r[1],
                "procedure_code": r[2],
                "urgency": r[3],
                "created_at": r[4],
                "approval_probability": float(r[5]) if r[5] else None
            }
            for r in requests
        ]
    }

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())

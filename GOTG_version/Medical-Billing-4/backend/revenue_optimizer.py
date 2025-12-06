"""
Revenue Optimizer - Financial tracking and sustainability calculation
Tracks medical billing revenue for Gift of the Givers sustainability
"""

import sqlite3
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RevenueAllocationModel(Enum):
    """Revenue allocation strategies for GOTG sustainability"""
    
    PERCENTAGE_BASED = "percentage"  # Fixed percentage per claim
    SLIDING_SCALE = "sliding"  # Scale based on claim amount
    OPERATIONAL_COST = "operational"  # Cover operational costs first
    IMPACT_BASED = "impact"  # Based on patient impact (emergency vs routine)


class RevenueOptimizer:
    """
    Financial tracking and optimization for Gift of the Givers
    
    Responsibilities:
    - Calculate revenue per claim
    - Track GOTG sustainability allocation
    - Generate financial reports
    - Forecast revenue projections
    - Optimize allocation strategies
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        # Revenue allocation percentages
        self.allocation_model = {
            'insurance_payment_to_gotg': 0.15,  # 15% of insurance payments
            'patient_responsibility_to_gotg': 0.10,  # 10% of patient responsibility
            'operational_overhead': 0.25,  # 25% for operations
            'staff_incentive': 0.10,  # 10% for billing staff bonuses
            'reinvestment': 0.05  # 5% for technology/improvements
        }
        
        # Operational cost targets
        self.monthly_operational_target = 5000.00  # $5000/month baseline
        self.emergency_response_markup = 0.20  # 20% additional revenue for emergencies
    
    # =====================================================
    # REVENUE CALCULATION
    # =====================================================
    
    def calculate_claim_revenue(self, claim_id: int) -> Dict[str, float]:
        """
        Calculate revenue breakdown for a single claim
        Returns: GOTG share, operational costs, staff incentive, etc.
        """
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get claim details
            cursor.execute("""
                SELECT 
                    c.id,
                    c.patient_id,
                    c.total_charge,
                    c.insurance_payment_estimate,
                    c.patient_responsibility,
                    c.claim_status,
                    c.service_date,
                    i.country
                FROM claims c
                LEFT JOIN patients p ON c.patient_id = p.id
                LEFT JOIN patient_insurance i ON p.id = i.patient_id
                WHERE c.id = ?
            """, (claim_id,))
            
            claim = cursor.fetchone()
            conn.close()
            
            if not claim:
                return {'error': 'Claim not found'}
            
            # Calculate revenue shares
            insurance_payment = float(claim['insurance_payment_estimate'] or 0)
            patient_resp = float(claim['patient_responsibility'] or 0)
            
            # Base allocation
            insurance_gotg_share = insurance_payment * self.allocation_model['insurance_payment_to_gotg']
            patient_gotg_share = patient_resp * self.allocation_model['patient_responsibility_to_gotg']
            
            total_gotg_revenue = insurance_gotg_share + patient_gotg_share
            
            # Apply emergency markup if applicable
            if self._is_emergency_service(claim['service_date']):
                total_gotg_revenue *= (1 + self.emergency_response_markup)
            
            # Calculate allocation breakdown
            allocation = {
                'claim_id': claim_id,
                'total_charge': float(claim['total_charge']),
                'insurance_payment': insurance_payment,
                'patient_responsibility': patient_resp,
                'gotg_revenue_total': total_gotg_revenue,
                'operational_costs': total_gotg_revenue * self.allocation_model['operational_overhead'],
                'staff_incentive': total_gotg_revenue * self.allocation_model['staff_incentive'],
                'reinvestment': total_gotg_revenue * self.allocation_model['reinvestment'],
                'calculation_date': datetime.now().isoformat()
            }
            
            return allocation
        
        except Exception as e:
            logger.error(f"Failed to calculate claim revenue: {e}")
            return {'error': str(e)}
    
    def calculate_portfolio_revenue(self, 
                                   start_date: str,
                                   end_date: str) -> Dict[str, Any]:
        """
        Calculate total revenue across all claims in date range
        Returns: Portfolio revenue summary with breakdowns
        """
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all submitted claims
            cursor.execute("""
                SELECT id, total_charge, insurance_payment_estimate, patient_responsibility
                FROM claims
                WHERE claim_status IN ('SUBMITTED', 'PAYMENT_RECEIVED')
                AND service_date BETWEEN ? AND ?
            """, (start_date, end_date))
            
            claims = cursor.fetchall()
            conn.close()
            
            if not claims:
                return {
                    'period': {'start': start_date, 'end': end_date},
                    'claim_count': 0,
                    'portfolio_revenue': 0
                }
            
            # Calculate portfolio totals
            total_charges = sum(float(c['total_charge']) for c in claims)
            total_insurance = sum(float(c['insurance_payment_estimate'] or 0) for c in claims)
            total_patient_resp = sum(float(c['patient_responsibility'] or 0) for c in claims)
            
            # Calculate GOTG revenue allocation
            gotg_from_insurance = total_insurance * self.allocation_model['insurance_payment_to_gotg']
            gotg_from_patient = total_patient_resp * self.allocation_model['patient_responsibility_to_gotg']
            total_gotg_revenue = gotg_from_insurance + gotg_from_patient
            
            portfolio = {
                'period': {'start': start_date, 'end': end_date},
                'claim_count': len(claims),
                'financial_summary': {
                    'total_charges': total_charges,
                    'total_insurance_payment': total_insurance,
                    'total_patient_responsibility': total_patient_resp,
                    'total_revenue_collected': total_insurance + total_patient_resp
                },
                'gotg_allocation': {
                    'from_insurance_payments': gotg_from_insurance,
                    'from_patient_responsibility': gotg_from_patient,
                    'total_gotg_revenue': total_gotg_revenue,
                    'operational_costs': total_gotg_revenue * self.allocation_model['operational_overhead'],
                    'staff_incentive': total_gotg_revenue * self.allocation_model['staff_incentive'],
                    'reinvestment_fund': total_gotg_revenue * self.allocation_model['reinvestment']
                },
                'metrics': {
                    'average_claim_value': total_charges / len(claims),
                    'average_insurance_payment': total_insurance / len(claims),
                    'collection_rate': (total_insurance + total_patient_resp) / total_charges if total_charges > 0 else 0
                }
            }
            
            return portfolio
        
        except Exception as e:
            logger.error(f"Failed to calculate portfolio revenue: {e}")
            return {'error': str(e)}
    
    def calculate_monthly_revenue_summary(self, year: int, month: int) -> Dict[str, Any]:
        """
        Calculate revenue summary for specific month
        Used for sustainability reporting
        """
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get month range
            start_date = f"{year:04d}-{month:02d}-01"
            
            if month == 12:
                end_date = f"{year+1:04d}-01-01"
            else:
                end_date = f"{year:04d}-{month+1:02d}-01"
            
            # Calculate revenue
            portfolio = self.calculate_portfolio_revenue(start_date, end_date)
            
            if 'error' in portfolio:
                return portfolio
            
            # Get stored revenue data
            cursor.execute("""
                SELECT SUM(gift_of_givers_share) as gotg_paid
                FROM revenue_tracking
                WHERE billing_month = ?
            """, (f"{year:04d}-{month:02d}",))
            
            paid_revenue = cursor.fetchone()
            conn.close()
            
            # Compare to operational target
            target = self.monthly_operational_target
            projected_gotg = portfolio['gotg_allocation']['total_gotg_revenue']
            actual_paid = float(paid_revenue[0] or 0)
            
            summary = {
                'year': year,
                'month': month,
                'claims_processed': portfolio['claim_count'],
                'projected_gotg_revenue': projected_gotg,
                'actual_gotg_paid': actual_paid,
                'operational_target': target,
                'target_achievement': min(100, (projected_gotg / target * 100)) if target > 0 else 0,
                'financial_details': portfolio['financial_summary'],
                'allocation_details': portfolio['gotg_allocation']
            }
            
            return summary
        
        except Exception as e:
            logger.error(f"Failed to calculate monthly revenue: {e}")
            return {'error': str(e)}
    
    # =====================================================
    # REVENUE PROJECTIONS & FORECASTING
    # =====================================================
    
    def project_annual_revenue(self, years_to_project: int = 1) -> Dict[str, Any]:
        """
        Project future revenue based on historical trends
        Uses claim volume and average values to forecast
        """
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get historical monthly data
            cursor.execute("""
                SELECT 
                    COUNT(*) as claim_count,
                    AVG(total_charge) as avg_claim_value,
                    AVG(COALESCE(insurance_payment_estimate, 0)) as avg_insurance,
                    STRFTIME('%Y-%m', service_date) as month
                FROM claims
                WHERE claim_status IN ('SUBMITTED', 'PAYMENT_RECEIVED')
                GROUP BY STRFTIME('%Y-%m', service_date)
                ORDER BY month DESC
                LIMIT 12
            """)
            
            historical_data = cursor.fetchall()
            conn.close()
            
            if not historical_data:
                return {'error': 'Insufficient historical data for projection'}
            
            # Calculate average metrics
            avg_monthly_claims = statistics.mean([row['claim_count'] for row in historical_data])
            avg_claim_value = statistics.mean([row['avg_claim_value'] for row in historical_data if row['avg_claim_value']])
            avg_insurance_payment = statistics.mean([row['avg_insurance'] for row in historical_data if row['avg_insurance']])
            
            # Project forward
            projection = {
                'projection_period': f"{years_to_project} year(s)",
                'historical_baseline': {
                    'avg_monthly_claims': avg_monthly_claims,
                    'avg_claim_value': avg_claim_value,
                    'avg_insurance_payment': avg_insurance_payment
                },
                'annual_projections': []
            }
            
            for year_offset in range(1, years_to_project + 1):
                # Project with conservative growth
                growth_factor = 1.05 ** year_offset  # 5% annual growth
                
                monthly_projected = avg_monthly_claims * growth_factor
                annual_claims = monthly_projected * 12
                annual_revenue = annual_claims * avg_insurance_payment
                
                gotg_share = annual_revenue * self.allocation_model['insurance_payment_to_gotg']
                
                projection['annual_projections'].append({
                    'year_offset': year_offset,
                    'projected_claims': int(annual_claims),
                    'projected_revenue': annual_revenue,
                    'projected_gotg_share': gotg_share,
                    'monthly_average': monthly_projected * avg_insurance_payment
                })
            
            return projection
        
        except Exception as e:
            logger.error(f"Failed to project revenue: {e}")
            return {'error': str(e)}
    
    def forecast_sustainability_timeline(self) -> Dict[str, Any]:
        """
        Forecast when billing revenue will fully sustain operations
        """
        
        try:
            projection = self.project_annual_revenue(years_to_project=3)
            
            if 'error' in projection:
                return projection
            
            # Find when operational target is met
            target = self.monthly_operational_target
            sustainable = False
            timeline = None
            
            for proj in projection['annual_projections']:
                monthly_avg_gotg = proj['monthly_average'] * self.allocation_model['operational_overhead']
                
                if monthly_avg_gotg >= target:
                    sustainable = True
                    timeline = f"Projected in {proj['year_offset']} year(s)"
                    break
            
            forecast = {
                'monthly_operational_target': target,
                'currently_sustainable': sustainable,
                'sustainability_timeline': timeline,
                'projections': projection['annual_projections']
            }
            
            return forecast
        
        except Exception as e:
            logger.error(f"Failed to forecast sustainability: {e}")
            return {'error': str(e)}
    
    # =====================================================
    # OPTIMIZATION STRATEGIES
    # =====================================================
    
    def recommend_allocation_optimization(self) -> Dict[str, Any]:
        """
        Analyze revenue and recommend optimization strategies
        """
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get last 3 months of data
            cursor.execute("""
                SELECT 
                    COUNT(*) as claim_count,
                    SUM(total_charge) as total_charges,
                    SUM(COALESCE(insurance_payment_estimate, 0)) as insurance_paid,
                    SUM(claim_status = 'REJECTED') as rejected_count
                FROM claims
                WHERE service_date >= date('now', '-90 days')
            """)
            
            recent = cursor.fetchone()
            conn.close()
            
            recommendations = {
                'period': 'Last 90 days',
                'metrics': {
                    'claims_processed': recent['claim_count'],
                    'total_charges': float(recent['total_charges'] or 0),
                    'insurance_collected': float(recent['insurance_paid'] or 0),
                    'rejection_rate': (recent['rejected_count'] / recent['claim_count']) if recent['claim_count'] > 0 else 0
                },
                'recommendations': []
            }
            
            # Analyze and recommend
            if recommendations['metrics']['rejection_rate'] > 0.10:
                recommendations['recommendations'].append({
                    'priority': 'HIGH',
                    'recommendation': 'Improve claim accuracy',
                    'reason': f"Rejection rate {recommendations['metrics']['rejection_rate']*100:.1f}% is above 10% benchmark",
                    'impact': 'Could recover ~5% additional revenue'
                })
            
            if recommendations['metrics']['claim_count'] < 10:
                recommendations['recommendations'].append({
                    'priority': 'HIGH',
                    'recommendation': 'Increase volume through marketing',
                    'reason': 'Processing volume is below optimal efficiency',
                    'impact': 'Could increase revenue by 50%+ with 2x volume'
                })
            
            return recommendations
        
        except Exception as e:
            logger.error(f"Failed to recommend optimization: {e}")
            return {'error': str(e)}
    
    # =====================================================
    # HELPER METHODS
    # =====================================================
    
    def _is_emergency_service(self, service_date: str) -> bool:
        """Check if service is emergency/after-hours"""
        
        try:
            from datetime import datetime
            service_dt = datetime.fromisoformat(service_date)
            
            # Emergency if weekend or after 5pm
            if service_dt.weekday() >= 5:  # Saturday or Sunday
                return True
            
            if service_dt.hour >= 17:  # After 5pm
                return True
            
            return False
        
        except Exception:
            return False
    
    def store_revenue_tracking(self,
                              claim_id: int,
                              billing_month: str,
                              total_charge: float,
                              insurance_payment: float,
                              patient_responsibility: float,
                              gotg_share: float) -> bool:
        """Store revenue tracking record"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO revenue_tracking
                (claim_id, billing_month, total_charge, insurance_payment, 
                 patient_responsibility, gift_of_givers_share)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (claim_id, billing_month, total_charge, insurance_payment, 
                  patient_responsibility, gotg_share))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stored revenue tracking for claim {claim_id}: ${gotg_share:.2f} GOTG share")
            return True
        
        except Exception as e:
            logger.error(f"Failed to store revenue tracking: {e}")
            return False

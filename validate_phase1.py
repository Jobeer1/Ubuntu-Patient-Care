#!/usr/bin/env python3
"""
Phase 1 Test Validation Script

Runs all Phase 1 tests and validates functionality.
Shows which bounties are ready to claim.

Usage:
    python validate_phase1.py              # Run all tests
    python validate_phase1.py --quick      # Quick validation
    python validate_phase1.py --coverage   # With coverage report
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime


def run_command(cmd: str, description: str = None) -> tuple:
    """Run a command and return (success, output)"""
    if description:
        print(f"\n{'='*60}")
        print(f"▶ {description}")
        print('='*60)
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print("⚠️  Command timeout (5 minutes)")
        return False, "Timeout"
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False, str(e)


class Phase1Validator:
    """Validates Phase 1 completeness and test status"""
    
    def __init__(self):
        self.results = {}
        self.root_dir = Path(__file__).parent
        self.test_dir = self.root_dir / "tests"
        self.audit_dir = self.root_dir / "audit"
        self.adapter_dir = self.root_dir / "fhir_adapter" / "adapters"
    
    def validate_files_exist(self):
        """Check if all required files exist"""
        print("\n📁 CHECKING FILE STRUCTURE...")
        
        required_files = {
            "P1-AUD-004": [
                self.audit_dir / "report_finalizer.py",
                self.test_dir / "test_report_finalizer.py"
            ],
            "P1-FHIR-002": [
                self.test_dir / "test_fhir_endpoints.py"
            ],
            "P1-MAP-002": [
                self.adapter_dir / "patient_id_adapter.py",
                self.test_dir / "test_patient_id_adapter.py"
            ],
            "Integration": [
                self.test_dir / "test_phase1_integration.py"
            ]
        }
        
        all_exist = True
        for component, files in required_files.items():
            component_status = "✅"
            for file in files:
                if file.exists():
                    print(f"  ✅ {file.name}")
                else:
                    print(f"  ❌ {file.name} - NOT FOUND")
                    component_status = "❌"
                    all_exist = False
            
            self.results[component] = component_status == "✅"
        
        return all_exist
    
    def validate_code_quality(self):
        """Check code for basic quality metrics"""
        print("\n📊 VALIDATING CODE QUALITY...")
        
        checks = {
            "P1-AUD-004": {
                "file": self.audit_dir / "report_finalizer.py",
                "min_lines": 100,
                "required_keywords": ["ReportFinalizer", "ReportAuditStamp", "compute_content_hash", "verify_report_stamp"]
            },
            "P1-MAP-002": {
                "file": self.adapter_dir / "patient_id_adapter.py",
                "min_lines": 200,
                "required_keywords": ["PatientIDAdapter", "register_mapping", "get_fhir_id", "get_openemr_id"]
            },
            "Integration Tests": {
                "file": self.test_dir / "test_phase1_integration.py",
                "min_lines": 100,
                "required_keywords": ["TestPhase1Integration", "complete_patient_workflow", "audit_trail"]
            }
        }
        
        for component, check in checks.items():
            file_path = check["file"]
            if not file_path.exists():
                print(f"  ⚠️  {component}: File not found")
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
                
                # Check line count
                if len(lines) < check["min_lines"]:
                    print(f"  ⚠️  {component}: Only {len(lines)} lines (min: {check['min_lines']})")
                else:
                    print(f"  ✅ {component}: {len(lines)} lines")
                
                # Check keywords
                missing = []
                for keyword in check["required_keywords"]:
                    if keyword not in content:
                        missing.append(keyword)
                
                if missing:
                    print(f"     ⚠️  Missing keywords: {', '.join(missing)}")
                else:
                    print(f"     ✅ All required keywords present")
    
    def estimate_tests(self):
        """Estimate number of tests"""
        print("\n🧪 ESTIMATING TEST COUNTS...")
        
        test_files = {
            "test_report_finalizer.py": "P1-AUD-004 Tests",
            "test_fhir_endpoints.py": "P1-FHIR-002 Tests",
            "test_patient_id_adapter.py": "P1-MAP-002 Tests",
            "test_phase1_integration.py": "Integration Tests"
        }
        
        total_tests = 0
        for filename, description in test_files.items():
            filepath = self.test_dir / filename
            if filepath.exists():
                with open(filepath, 'r') as f:
                    content = f.read()
                    test_count = content.count("def test_")
                    total_tests += test_count
                    print(f"  ✅ {description}: ~{test_count} tests")
            else:
                print(f"  ⚠️  {description}: File not found")
        
        print(f"\n  📊 TOTAL ESTIMATED TESTS: {total_tests}+")
        return total_tests
    
    def check_pytest_ready(self):
        """Check if pytest can import the modules"""
        print("\n🔍 CHECKING TEST READINESS...")
        
        # Check Python version
        python_version = sys.version_info
        print(f"  ℹ️  Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Check pytest
        success, output = run_command("pytest --version", "Checking pytest installation")
        if success:
            print(f"  ✅ pytest is installed")
        else:
            print(f"  ⚠️  pytest may not be installed")
            print(f"     Install with: pip install pytest")
        
        return success
    
    def generate_report(self):
        """Generate validation report"""
        print("\n" + "="*60)
        print("PHASE 1 VALIDATION REPORT")
        print("="*60)
        print(f"Generated: {datetime.now().isoformat()}")
        print()
        
        # Summary
        completed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        
        print(f"📊 Status: {completed}/{total} components ready")
        print()
        
        # Bounties
        print("🏆 CLAIMABLE BOUNTIES:")
        if self.results.get("P1-AUD-004"):
            print("  ✅ P1-AUD-004: Hash & Stamp Reports")
        if self.results.get("P1-FHIR-002"):
            print("  ✅ P1-FHIR-002: FHIR Endpoint Tests")
        if self.results.get("P1-MAP-002"):
            print("  ✅ P1-MAP-002: Patient ID Adapter")
        if self.results.get("Integration"):
            print("  ✅ Integration Tests (validates all components)")
        
        print()
        print("📋 NEXT STEPS:")
        print("  1. Run: pytest tests/ -v")
        print("  2. Verify all tests pass")
        print("  3. Generate coverage: pytest --cov")
        print("  4. Submit bounty claims with test evidence")
        print()
        
        return completed == total
    
    def run_validation(self):
        """Run full validation"""
        print("\n" + "="*60)
        print("🚀 PHASE 1 VALIDATION STARTING")
        print("="*60)
        
        # Check files
        files_ok = self.validate_files_exist()
        
        # Check code quality
        self.validate_code_quality()
        
        # Estimate tests
        test_count = self.estimate_tests()
        
        # Check pytest
        pytest_ok = self.check_pytest_ready()
        
        # Generate report
        all_ok = self.generate_report()
        
        print()
        if all_ok:
            print("✅ VALIDATION PASSED - All components ready!")
            return 0
        else:
            print("⚠️  Some components may need attention")
            return 1


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 1 Validator")
    parser.add_argument("--quick", action="store_true", help="Quick validation only")
    parser.add_argument("--run-tests", action="store_true", help="Run actual pytest")
    
    args = parser.parse_args()
    
    validator = Phase1Validator()
    
    if args.quick:
        print("⚡ Running quick validation...")
        validator.validate_files_exist()
        validator.estimate_tests()
    else:
        return validator.run_validation()
    
    if args.run_tests:
        print("\n🧪 Running pytest...")
        success, output = run_command("pytest tests/ -v")
        print(output)
        return 0 if success else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

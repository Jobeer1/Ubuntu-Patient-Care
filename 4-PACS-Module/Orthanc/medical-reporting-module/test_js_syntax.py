#!/usr/bin/env python3
"""
Test JavaScript syntax by running it through a basic validator
"""

import os
import sys
import subprocess
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_javascript_syntax():
    """Test JavaScript syntax using Node.js if available"""
    try:
        js_file = 'frontend/static/js/voice-demo.js'
        
        if not os.path.exists(js_file):
            logger.error(f"❌ JavaScript file not found: {js_file}")
            return False
        
        # Try to validate with Node.js
        try:
            result = subprocess.run([
                'node', '-c', js_file
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info("✅ JavaScript syntax is valid")
                return True
            else:
                logger.error(f"❌ JavaScript syntax error: {result.stderr}")
                return False
                
        except FileNotFoundError:
            logger.warning("⚠️ Node.js not available, checking file manually")
            
            # Basic manual check
            with open(js_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for common syntax issues
            issues = []
            
            # Check for Python-style docstrings
            if '"""' in content:
                issues.append("Python-style docstrings found (should use // or /* */)")
            
            # Check for unmatched braces
            open_braces = content.count('{')
            close_braces = content.count('}')
            if open_braces != close_braces:
                issues.append(f"Unmatched braces: {open_braces} open, {close_braces} close")
            
            # Check for unmatched parentheses
            open_parens = content.count('(')
            close_parens = content.count(')')
            if open_parens != close_parens:
                issues.append(f"Unmatched parentheses: {open_parens} open, {close_parens} close")
            
            if issues:
                logger.error("❌ JavaScript issues found:")
                for issue in issues:
                    logger.error(f"   - {issue}")
                return False
            else:
                logger.info("✅ Basic JavaScript syntax checks passed")
                return True
                
    except Exception as e:
        logger.error(f"❌ JavaScript test failed: {e}")
        return False

def test_css_exists():
    """Test that CSS file exists"""
    css_file = 'frontend/static/css/sa-dashboard.css'
    
    if os.path.exists(css_file):
        logger.info("✅ CSS file exists")
        return True
    else:
        logger.error("❌ CSS file missing")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Testing JavaScript and CSS files...")
    
    js_test = test_javascript_syntax()
    css_test = test_css_exists()
    
    logger.info("\n📋 Test Summary:")
    logger.info(f"JavaScript syntax: {'✅ PASS' if js_test else '❌ FAIL'}")
    logger.info(f"CSS file: {'✅ PASS' if css_test else '❌ FAIL'}")
    
    if js_test and css_test:
        logger.info("🎉 All tests passed! The STT interface should work now.")
        return True
    else:
        logger.error("❌ Some tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
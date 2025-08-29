#!/usr/bin/env python3
"""
Fix syntax issues in the SA Medical Dashboard
"""

import os
import re

def fix_routes_file():
    """Fix any syntax issues in routes.py"""
    routes_file = 'core/routes.py'
    
    if not os.path.exists(routes_file):
        print(f"❌ {routes_file} not found")
        return False
    
    try:
        with open(routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix common syntax issues
        fixes_made = []
        
        # Fix broken decorators
        if '@c\nore_bp.route(' in content:
            content = content.replace('@c\nore_bp.route(', '@core_bp.route(')
            fixes_made.append("Fixed broken decorator")
        
        # Fix any other line break issues in decorators
        content = re.sub(r'@c\s*ore_bp\.route\(', '@core_bp.route(', content)
        
        # Ensure proper indentation
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Fix common indentation issues
            if line.strip().startswith('@core_bp.route(') and i > 0:
                # Ensure decorator is at the same level as previous function
                if fixed_lines and not fixed_lines[-1].strip():
                    fixed_lines.append(line)
                else:
                    fixed_lines.append('\n' + line)
            else:
                fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)
        
        # Write back the fixed content
        with open(routes_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if fixes_made:
            print(f"✅ Fixed routes.py: {', '.join(fixes_made)}")
        else:
            print("✅ routes.py looks good")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing routes.py: {e}")
        return False

def test_import():
    """Test if we can import the routes module"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from core.routes import core_bp
        print("✅ Successfully imported core.routes")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def main():
    """Main fix function"""
    print("🔧 Fixing SA Medical Dashboard syntax issues...")
    
    # Fix routes file
    if fix_routes_file():
        print("✅ Routes file fixed")
    else:
        print("❌ Failed to fix routes file")
        return False
    
    # Test import
    if test_import():
        print("✅ Import test passed")
    else:
        print("❌ Import test failed")
        return False
    
    print("\n🎉 SA Medical Dashboard is ready to start!")
    print("Run: python app.py")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
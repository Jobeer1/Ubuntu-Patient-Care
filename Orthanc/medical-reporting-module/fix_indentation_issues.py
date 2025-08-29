#!/usr/bin/env python3
"""
Fix indentation issues in Python files
"""

import os
import re
from pathlib import Path

def fix_indentation_issues():
    """Fix common indentation issues in Python files"""
    
    current_dir = Path(__file__).parent
    
    # Files to check and fix
    files_to_check = [
        'services/security_service.py',
        'services/layout_manager.py',
        'services/audit_service.py',
        'services/cache_service.py'
    ]
    
    fixed_files = []
    
    for file_path in files_to_check:
        full_path = current_dir / file_path
        
        if not full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue
            
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix pattern: "#\n Global" -> "# Global"
            content = re.sub(r'#\n Global', '# Global', content)
            
            # Fix pattern: "#\n [word]" -> "# [word]"
            content = re.sub(r'#\n ([A-Za-z])', r'# \1', content)
            
            # Fix any standalone # followed by indented text
            content = re.sub(r'^#$\n^ ', '# ', content, flags=re.MULTILINE)
            
            if content != original_content:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files.append(file_path)
                print(f"✅ Fixed indentation in: {file_path}")
            else:
                print(f"✓ No issues found in: {file_path}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    if fixed_files:
        print(f"\n🔧 Fixed {len(fixed_files)} files:")
        for file_path in fixed_files:
            print(f"   - {file_path}")
    else:
        print("\n✅ No indentation issues found!")
    
    return len(fixed_files) > 0

if __name__ == '__main__':
    print("Fixing indentation issues...")
    print("-" * 40)
    
    fixed = fix_indentation_issues()
    
    if fixed:
        print("\n🎉 Indentation issues have been fixed!")
        print("Try running the app again: python app.py")
    else:
        print("\n✅ No indentation issues to fix!")
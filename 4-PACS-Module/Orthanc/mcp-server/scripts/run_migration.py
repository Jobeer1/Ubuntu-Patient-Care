#!/usr/bin/env python3
"""
Database Migration Runner
Runs SQL migration scripts on the MCP server database
"""
import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "mcp_server.db"
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"

def backup_database():
    """Create a backup of the database before migration"""
    if not DB_PATH.exists():
        print(f"⚠️  Database not found: {DB_PATH}")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.parent / f"mcp_server_backup_{timestamp}.db"
    
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def run_migration(migration_file):
    """Run a migration SQL file"""
    # Handle both relative and absolute paths
    if os.path.isabs(migration_file):
        migration_path = Path(migration_file)
    else:
        migration_path = MIGRATIONS_DIR / migration_file
    
    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_path}")
        return False
    
    print(f"\n📋 Running migration: {migration_file}")
    print("=" * 60)
    
    # Read migration SQL
    try:
        with open(migration_path, 'r', encoding='utf-8') as f:
            sql = f.read()
    except Exception as e:
        print(f"❌ Failed to read migration file: {e}")
        return False
    
    # Connect to database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Execute migration
        cursor.executescript(sql)
        conn.commit()
        
        print("✅ Migration executed successfully")
        
        # Verify tables created
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name;
        """)
        tables = cursor.fetchall()
        
        print(f"\n📊 Database tables ({len(tables)}):")
        for table in tables:
            print(f"   - {table[0]}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        return False

def verify_migration():
    """Verify migration was successful"""
    print("\n🔍 Verifying migration...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check for new tables
        expected_tables = [
            'patient_relationships',
            'doctor_patient_assignments',
            'family_access',
            'pacs_connection_config',
            'access_audit_log'
        ]
        
        for table in expected_tables:
            cursor.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cursor.fetchone()[0] == 0:
                print(f"❌ Table not found: {table}")
                return False
            else:
                print(f"✅ Table exists: {table}")
        
        # Check indexes
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        index_count = cursor.fetchone()[0]
        print(f"✅ Indexes created: {index_count}")
        
        # Check config values
        cursor.execute("SELECT COUNT(*) FROM pacs_connection_config")
        config_count = cursor.fetchone()[0]
        print(f"✅ Config entries: {config_count}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Main migration runner"""
    print("\n" + "=" * 60)
    print("MCP Server Database Migration")
    print("=" * 60)
    
    # Check if migration file specified
    if len(sys.argv) < 2:
        print("\nUsage: python run_migration.py <migration_file>")
        print("\nAvailable migrations:")
        if MIGRATIONS_DIR.exists():
            for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
                print(f"  - {file.name}")
        else:
            print("  No migrations found")
        sys.exit(1)
    
    migration_file = sys.argv[1]
    
    # Backup database
    print("\n📦 Creating backup...")
    backup_path = backup_database()
    if not backup_path:
        response = input("\n⚠️  Continue without backup? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Migration cancelled")
            sys.exit(1)
    
    # Run migration
    success = run_migration(migration_file)
    
    if not success:
        print("\n❌ Migration failed!")
        if backup_path:
            print(f"💾 Restore from backup: {backup_path}")
        sys.exit(1)
    
    # Verify migration
    if verify_migration():
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        if backup_path:
            print(f"\n💾 Backup saved: {backup_path}")
        print("\n📝 Next steps:")
        print("   1. Test with sample data")
        print("   2. Proceed to Task 1.2 (PACS Connector)")
    else:
        print("\n⚠️  Migration completed but verification failed")
        print("   Please check the database manually")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
NAS Configuration Management CLI
Utility to manage and switch between NAS paths for indexing operations
"""

import sys
import os
import json
from pathlib import Path

# Add backend to path
backend_dir = os.path.dirname(__file__)
sys.path.insert(0, backend_dir)

from config.nas_configuration import (
    get_nas_config,
    get_active_nas_path,
    set_active_nas_by_alias,
    reload_nas_config
)


def show_menu():
    """Display the main menu"""
    print("\n" + "=" * 80)
    print("NAS Configuration Management")
    print("=" * 80)
    print("\n1. Show Active NAS Configuration")
    print("2. Show All Available NAS Configurations")
    print("3. Switch to Different NAS")
    print("4. Show Current NAS Details")
    print("5. Save New Configuration")
    print("0. Exit\n")


def show_active_config():
    """Show the currently active NAS configuration"""
    config = get_nas_config()
    active_path = config.get_active_nas_path()
    active_config = config.get_active_nas_config()
    
    print("\n" + "-" * 80)
    print("📍 ACTIVE NAS CONFIGURATION")
    print("-" * 80)
    print(f"Path: {active_path}")
    print(f"Description: {active_config.get('description', 'N/A')}")
    print(f"Modalities: {', '.join(active_config.get('modalities', []))}")
    print(f"Enabled: {active_config.get('enabled', False)}")
    print("-" * 80)


def show_all_configs():
    """Show all available NAS configurations"""
    config = get_nas_config()
    configs = config.get_nas_configs()
    active_alias = config.config.get('active_alias', 'unknown')
    
    print("\n" + "-" * 80)
    print("📚 ALL NAS CONFIGURATIONS")
    print("-" * 80)
    
    for alias, cfg in configs.items():
        is_active = " ⭐ ACTIVE" if alias == active_alias else ""
        status = "✅ ENABLED" if cfg.get('enabled') else "❌ DISABLED"
        print(f"\n{alias}{is_active}")
        print(f"  Status: {status}")
        print(f"  Path: {cfg['path']}")
        print(f"  Description: {cfg['description']}")
        print(f"  Modalities: {', '.join(cfg.get('modalities', []))}")
    
    print("\n" + "-" * 80)


def switch_nas():
    """Switch to a different NAS configuration"""
    config = get_nas_config()
    configs = config.get_nas_configs()
    
    print("\n" + "-" * 80)
    print("🔄 SWITCH NAS CONFIGURATION")
    print("-" * 80)
    
    print("\nAvailable configurations:")
    aliases = list(configs.keys())
    for i, alias in enumerate(aliases, 1):
        cfg = configs[alias]
        status = "✅" if cfg.get('enabled') else "❌"
        print(f"{i}. {alias} {status}")
        print(f"   {cfg['path']}")
        print(f"   {cfg['description']}")
    
    try:
        choice = input(f"\nEnter selection (1-{len(aliases)}): ").strip()
        idx = int(choice) - 1
        if 0 <= idx < len(aliases):
            selected_alias = aliases[idx]
            if set_active_nas_by_alias(selected_alias):
                print(f"\n✅ Successfully switched to: {selected_alias}")
                reload_nas_config()
                show_active_config()
            else:
                print(f"\n❌ Failed to switch to: {selected_alias}")
        else:
            print("❌ Invalid selection")
    except ValueError:
        print("❌ Invalid input")


def show_current_details():
    """Show detailed information about current NAS"""
    active_path = get_active_nas_path()
    
    print("\n" + "-" * 80)
    print("🔍 CURRENT NAS DETAILS")
    print("-" * 80)
    print(f"Active NAS Path: {active_path}")
    
    # Try to check accessibility
    try:
        if os.path.exists(active_path):
            print("✅ NAS is currently accessible")
            # Get folder count (limit to avoid long waits)
            try:
                import os
                items = []
                for item in os.listdir(active_path)[:10]:
                    full_path = os.path.join(active_path, item)
                    items.append(f"  - {item}")
                
                print(f"\nFirst 10 items in NAS:")
                for item in items:
                    print(item)
                
                total = len(os.listdir(active_path))
                print(f"\nTotal items: {total}")
            except Exception as e:
                print(f"Could not list contents: {e}")
        else:
            print("❌ NAS is not currently accessible")
    except Exception as e:
        print(f"⚠️  Error checking NAS accessibility: {e}")
    
    print("-" * 80)


def save_new_configuration():
    """Save a new NAS configuration"""
    print("\n" + "-" * 80)
    print("➕ ADD NEW NAS CONFIGURATION")
    print("-" * 80)
    
    try:
        alias = input("Enter configuration alias (e.g., 'archive_2'): ").strip()
        path = input("Enter UNC path (e.g., \\\\192.168.1.100\\Share): ").strip()
        description = input("Enter description: ").strip()
        modalities = input("Enter modalities (comma-separated, e.g., CT,MR,US): ").strip()
        enabled = input("Enable this configuration? (y/n): ").strip().lower() == 'y'
        
        config = get_nas_config()
        configs = config.config.get('configs', {})
        
        # Add new configuration
        configs[alias] = {
            'path': path,
            'description': description,
            'modalities': [m.strip() for m in modalities.split(',')],
            'enabled': enabled
        }
        
        config.config['configs'] = configs
        
        # Save
        import json
        config_file = os.path.join(os.path.dirname(__file__), 'config', 'nas_settings.json')
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config.config, f, indent=2)
        
        print(f"\n✅ Configuration '{alias}' saved successfully!")
        if enabled:
            set_active_nas_by_alias(alias)
            reload_nas_config()
            print(f"✅ Switched to '{alias}' as active NAS")
        
    except Exception as e:
        print(f"\n❌ Error saving configuration: {e}")


def main():
    """Main CLI loop"""
    print("\n🚀 NAS Configuration Manager")
    print("Switch between different NAS paths for indexing operations")
    
    while True:
        show_menu()
        choice = input("Select option: ").strip()
        
        if choice == '1':
            show_active_config()
        elif choice == '2':
            show_all_configs()
        elif choice == '3':
            switch_nas()
        elif choice == '4':
            show_current_details()
        elif choice == '5':
            save_new_configuration()
        elif choice == '0':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid option. Please try again.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

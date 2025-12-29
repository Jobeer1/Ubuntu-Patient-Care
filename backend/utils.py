from .extensions import db
from .models import User, Group
import uuid
import json

def init_default_groups():
    """Create default public groups if they don't exist"""
    defaults = [
        "General", "Announcements", "Doctors", "Nurses", 
        "Emergency", "Radiology", "Pathology", "Admin", 
        "Social", "Tech Support"
    ]
    
    try:
        # Check if we have any public groups
        existing = Group.query.filter_by(is_private=False).count()
        if existing >= len(defaults):
            print(f"✅ Found {existing} default groups")
            return
            
        # Create system user for group creation
        sys_user = User.query.get('SYSTEM')
        if not sys_user:
            sys_user = User(user_id='SYSTEM', alias='System', pin_hash='SYSTEM')
            db.session.add(sys_user)
            
        # Create The Forge Agent User
        forge_user = User.query.get('FORGE')
        if not forge_user:
            forge_user = User(user_id='FORGE', alias='The Forge', pin_hash='FORGE', alias_colors='{"0":"#ff0000","1":"#ff0000","2":"#ff0000","3":"#ff0000","4":"#ff0000","5":"#ff0000","6":"#ff0000","7":"#ff0000","8":"#ff0000"}')
            db.session.add(forge_user)

        # Create Quest Master User
        quest_user = User.query.get('QUEST')
        if not quest_user:
            quest_user = User(user_id='QUEST', alias='Quest Master', pin_hash='QUEST', alias_colors='{"0":"#ffaa00","1":"#ffaa00","2":"#ffaa00","3":"#ffaa00","4":"#ffaa00","5":"#ffaa00","6":"#ffaa00","7":"#ffaa00","8":"#ffaa00"}')
            db.session.add(quest_user)
            
        db.session.commit()
            
        for name in defaults:
            # Check if group already exists
            if not Group.query.filter_by(group_name=name).first():
                group = Group(
                    id=str(uuid.uuid4()),
                    group_name=name,
                    created_by='SYSTEM',
                    is_private=False
                )
                db.session.add(group)
        
        db.session.commit()
        final_count = Group.query.filter_by(is_private=False).count()
        print(f"✅ Ensured {final_count} default groups exist")
    except Exception as e:
        print(f"⚠️ Error creating default groups: {e}")
        db.session.rollback()

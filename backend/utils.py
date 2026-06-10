from .extensions import db
from .models import User, Group, Message, Quest, QuestStory
import uuid
import json

def init_default_groups():
    """Create default public groups if they don't exist"""
    defaults = [
        "General", "Announcements", "Doctors", "Nurses", 
        "Emergency", "Radiology", "Pathology", "Admin", 
        "Social", "Tech Support", "Quest Board"
    ]
    
    try:
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

        # Create SDOH Navigator User
        sdoh_user = User.query.get('SDOH')
        if not sdoh_user:
            sdoh_user = User(
                user_id='SDOH',
                alias='SDOH Navigator',
                pin_hash='SDOH',
                alias_colors='{"0":"#00ffff","1":"#00ffff","2":"#00ffff","3":"#00ffff","4":"#00ffff","5":"#00ffff","6":"#00ffff","7":"#00ffff","8":"#00ffff"}'
            )
            db.session.add(sdoh_user)
            
        db.session.commit()

        # Check if we have any public groups
        existing = Group.query.filter_by(is_private=False).count()
        if existing >= len(defaults):
            print(f"✅ Found {existing} default groups")
        else:
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

        # Initialize Default Quests
        rebuilding_trust = Quest.query.filter_by(name='Rebuilding Trust').first()
        if not rebuilding_trust:
            rebuilding_trust = Quest(
                id=str(uuid.uuid4()),
                name='Rebuilding Trust',
                description='You have confessed to infidelity. Now you must face the consequences and begin the long journey of rebuilding trust with your spouse.',
                start_location='Your Home (Living Room)',
                end_goal='Rebuild trust and emotional safety with your spouse.',
                requirements='[]',
                difficulty='solo',
                created_by='QUEST',
                reward='50 XP + "(level1 trust rebuilder)"'
            )
            db.session.add(rebuilding_trust)
            db.session.commit()
            print("✅ Initialized 'Rebuilding Trust' quest")
            
            # Post to Quest Board
            quest_board = Group.query.filter_by(group_name='Quest Board').first()
            if quest_board:
                quest_data = {
                    "title": rebuilding_trust.name,
                    "description": rebuilding_trust.description,
                    "start_location": rebuilding_trust.start_location,
                    "end_goal": rebuilding_trust.end_goal,
                    "xp": 50,
                    "requirements": [],
                    "source": "quest_master"
                }
                msg = Message(
                    msg_id=str(uuid.uuid4()),
                    sender_id='QUEST',
                    chat_id=quest_board.id,
                    content=f"[QUEST_DATA] {json.dumps(quest_data)}"
                )
                db.session.add(msg)
                db.session.commit()
                print("✅ Posted 'Rebuilding Trust' to Quest Board")

        # Initialize 'Rebuilding from Scratch' Quest
        rebuilding_scratch = Quest.query.filter_by(name='Rebuilding from Scratch').first()
        if not rebuilding_scratch:
            rebuilding_scratch = Quest(
                id=str(uuid.uuid4()),
                name='Rebuilding from Scratch',
                description='You have lost everything. You must explain your survival strategy and how you rebuild your life from zero.',
                start_location='A Cold Street Corner (Homeless)',
                end_goal='Recover your life to a state of stability and purpose, better than before.',
                requirements='[]',
                difficulty='solo',
                created_by='QUEST',
                reward='100 XP + "(Phoenix Risen)"'
            )
            db.session.add(rebuilding_scratch)
            db.session.commit()
            print("✅ Initialized 'Rebuilding from Scratch' quest")
            
            # Post to Quest Board
            quest_board = Group.query.filter_by(group_name='Quest Board').first()
            if quest_board:
                quest_data = {
                    "title": rebuilding_scratch.name,
                    "description": rebuilding_scratch.description,
                    "start_location": rebuilding_scratch.start_location,
                    "end_goal": rebuilding_scratch.end_goal,
                    "xp": 100,
                    "requirements": [],
                    "source": "quest_master"
                }
                msg = Message(
                    msg_id=str(uuid.uuid4()),
                    sender_id='QUEST',
                    chat_id=quest_board.id,
                    content=f"[QUEST_DATA] {json.dumps(quest_data)}"
                )
                db.session.add(msg)
                db.session.commit()
                print("✅ Posted 'Rebuilding from Scratch' to Quest Board")

        # Initialize 'Getting the Sale' Quest
        getting_sale = Quest.query.filter_by(name='Getting the Sale').first()
        if not getting_sale:
            getting_sale = Quest(
                id=str(uuid.uuid4()),
                name='Getting the Sale',
                description='Design a product, build it, and convince a stranger to pay real money for it. Balance quality, pricing, and persuasion.',
                start_location='A Workshop',
                end_goal='Make your first sale to a stranger.',
                requirements='[]',
                difficulty='solo',
                created_by='QUEST',
                reward='75 XP + "(Master Artisan)"'
            )
            db.session.add(getting_sale)
            db.session.commit()
            print("✅ Initialized 'Getting the Sale' quest")
            
            # Post to Quest Board
            quest_board = Group.query.filter_by(group_name='Quest Board').first()
            if quest_board:
                quest_data = {
                    "title": getting_sale.name,
                    "description": getting_sale.description,
                    "start_location": getting_sale.start_location,
                    "end_goal": getting_sale.end_goal,
                    "xp": 75,
                    "requirements": [],
                    "source": "quest_master"
                }
                msg = Message(
                    msg_id=str(uuid.uuid4()),
                    sender_id='QUEST',
                    chat_id=quest_board.id,
                    content=f"[QUEST_DATA] {json.dumps(quest_data)}"
                )
                db.session.add(msg)
                db.session.commit()
                print("✅ Posted 'Getting the Sale' to Quest Board")

        # Initialize 'The Climb' Quest
        the_climb = Quest.query.filter_by(name='The Climb').first()
        if not the_climb:
            the_climb = Quest(
                id=str(uuid.uuid4()),
                name='The Climb',
                description='Formulate a strategy, execute the job hunt, and secure a job offer. Overcome the Inner Critic and the grind of the application process.',
                start_location='Your Apartment (In Pajamas)',
                end_goal='Secure a job offer.',
                requirements='[]',
                difficulty='solo',
                created_by='QUEST',
                reward='80 XP + "(The Ascendant)"'
            )
            db.session.add(the_climb)
            db.session.commit()
            print("✅ Initialized 'The Climb' quest")
            
            # Post to Quest Board
            quest_board = Group.query.filter_by(group_name='Quest Board').first()
            if quest_board:
                quest_data = {
                    "title": the_climb.name,
                    "description": the_climb.description,
                    "start_location": the_climb.start_location,
                    "end_goal": the_climb.end_goal,
                    "xp": 80,
                    "requirements": [],
                    "source": "quest_master"
                }
                msg = Message(
                    msg_id=str(uuid.uuid4()),
                    sender_id='QUEST',
                    chat_id=quest_board.id,
                    content=f"[QUEST_DATA] {json.dumps(quest_data)}"
                )
                db.session.add(msg)
                db.session.commit()
                print("✅ Posted 'The Climb' to Quest Board")

        # Initialize 'The Heart's Compass' Quest
        hearts_compass = Quest.query.filter_by(name="The Heart's Compass").first()
        if not hearts_compass:
            hearts_compass = Quest(
                id=str(uuid.uuid4()),
                name="The Heart's Compass",
                description="Establish a genuine connection and secure a second date with a potential life partner. Navigate the complexities of authenticity and vulnerability.",
                start_location='A Wedding Reception',
                end_goal='Secure a second date with a potential life partner.',
                requirements='[]',
                difficulty='solo',
                created_by='QUEST',
                reward='60 XP + "(The Kindred Spirit)"'
            )
            db.session.add(hearts_compass)
            db.session.commit()
            print("✅ Initialized 'The Heart's Compass' quest")
            
            # Post to Quest Board
            quest_board = Group.query.filter_by(group_name='Quest Board').first()
            if quest_board:
                quest_data = {
                    "title": hearts_compass.name,
                    "description": hearts_compass.description,
                    "start_location": hearts_compass.start_location,
                    "end_goal": hearts_compass.end_goal,
                    "xp": 60,
                    "requirements": [],
                    "source": "quest_master"
                }
                msg = Message(
                    msg_id=str(uuid.uuid4()),
                    sender_id='QUEST',
                    chat_id=quest_board.id,
                    content=f"[QUEST_DATA] {json.dumps(quest_data)}"
                )
                db.session.add(msg)
                db.session.commit()
                print("✅ Posted 'The Heart's Compass' to Quest Board")

        # Initialize Sample Stories for Hall of Heroes
        if QuestStory.query.count() == 0:
            samples = [
                {
                    "user_alias": "Jobeer",
                    "quest_name": "Texas Sovereign Mesh",
                    "title": "Recruiting the Iron Man",
                    "content": "A high-stakes deliberation between Jobeer (The Architect) and Masha (The Librarian) regarding the recruitment of Elon Musk for the Texas Sovereign Mesh project. Analysis focused on Musk's 'Foundational Infrastructure' (Starlink, Gigafactory) versus the Mesh's 'Human BIOS' principles. While Musk provides 'Hardware Saturation' and 'Technological Velocity,' the challenge was ensuring his centralized power serves distributed community sovereignty. Jobeer ultimately decided that Musk's genuine care for Texas overrode methodological differences. The secure channel was opened, and the Architect invited the Builder to the war room to solve the objective together.",
                    "voice_note_url": "/sdoh/voices/Elon_Interactions_Full.mp3"
                },
                {
                    "user_alias": "Jobeer",
                    "quest_name": "UK Sovereignty",
                    "title": "The British Industrial Renaissance",
                    "content": "A tense negotiation between the Architect (Jobeer) and Sir James Dyson regarding the revival of British manufacturing. Jobeer details the success of Phase 2 in Leeds and Sheffield—producing 850,000 micro-wind turbines—and the Manchester graphene surge. Despite Dyson's initial skepticism and demand for 'blueprints,' Jobeer explains that the true blueprint is deep human reconnaissance (Phase 1) followed by matching and empowering individuals based on their 'jagged edges.' Dyson is challenged to lead his people and transform 'micro-production moats' into global ones, leveraging the diverse talents of the Architect's team.",
                    "voice_note_url": "/sdoh/voices/James_Dyson_Full_Interaction.mp3"
                },
                {
                    "user_alias": "Jobeer",
                    "quest_name": "The Uzbek-Vermaak Protocol",
                    "title": "The Forge of Legacy",
                    "content": "A high-stakes negotiation between Jobeer (The Architect) and Johann Rupert regarding the 'Crisis of Artisanal Succession' and the existential threat to cultural continuity. Jobeer diagnoses the 'extinction event' caused by the rot of traditional systems and proposes a radical restructuring: mapping every individual's 'jagged edges' to transition from independence to interdependency. Rupert is challenged to find the 'soul' of this new dynasty—moving beyond spreadsheets to reignite the primal fire of creation and legacy.",
                    "voice_note_url": "/sdoh/voices/Johann_Interactions_Full.mp3"
                },
                {
                    "user_alias": "Jobeer",
                    "quest_name": "Family Foundations",
                    "title": "The Quest for Annelise",
                    "content": "A deeply personal operation where Jobeer (The Architect) challenges Kira (The Trust Architect) to look beyond community metrics and help him find a life partner. Jobeer defines his 'three pillars of human happiness': Agency, Interdependency, and Transcendence. He seeks an Afrikaans lady who is a 'better social engineer' than Kira—someone who doesn't just understand the 'Human BIOS' but can live it. The resulting connection with Annelise (The Empath) becomes the cornerstone of his personal resilience. This interaction documents the moment the Architect realized that 'diamond grinds diamond' and that a powerful partnership requires friction, mutual refinement, and shared purpose.",
                    "voice_note_url": "/sdoh/voices/Romance_Annelise_Part_1.wav"
                },
                {
                    "user_alias": "Jobeer",
                    "quest_name": "The Big 6 & Silas Croft Partnership",
                    "title": "The Tale of Jobeer",
                    "content": "Hero presented the 'Big 6' and counter-offered Silas a 48-hour window to prove his capital's velocity. Silas accepted the challenge. Hero issued specific, time-bound operational requirements for Masha (infrastructure) and Uri (market leverage). Hero initiated a Real-Time Resource Monitor with a 48-hour TTL to track Silas's performance. Silas Croft formally accepted the challenge and confirmed he is 'game' to meet the demands within the stipulated timeframe. This was the beginning of a legendary alliance that would reshape the market landscape forever."
                },
                {
                    "user_alias": "Ironclad",
                    "quest_name": "Rebuilding Trust",
                    "title": "The Long Walk Home",
                    "content": "I stood in the living room, the weight of my confession like a physical burden. Elara's eyes were hollow. I didn't make excuses. I just listened. We went to see Dr. Sharma. It was brutal, but for the first time in years, we were actually talking. I learned that trust isn't rebuilt with one big gesture, but with a thousand small, honest moments. Every day since then has been a choice. A choice to be present, to be honest, and to show up even when it's hard. We aren't where we were, but we're moving forward, one step at a time."
                },
                {
                    "user_alias": "ShadowWalker",
                    "quest_name": "The Climb",
                    "title": "Silencing the Critic",
                    "content": "The rejection emails were piling up. My Inner Critic was screaming that I was a failure. I decided to stop applying to everything and focused on one high-value target. I reached out to an old contact, refined my portfolio, and finally got the interview with Mr. Thorne. I was honest about my past failures, and he respected that. I start on Monday. The lesson I learned was that the loudest voice in the room isn't always the one telling the truth. Sometimes, you have to silence the noise to hear the opportunity."
                }
            ]
            for s in samples:
                story = QuestStory(
                    id=str(uuid.uuid4()),
                    user_id='SYSTEM',
                    user_alias=s['user_alias'],
                    quest_name=s['quest_name'],
                    title=s['title'],
                    content=s['content'],
                    voice_note_url=s.get('voice_note_url'),
                    likes=5
                )
                db.session.add(story)
            db.session.commit()
            print("✅ Initialized sample stories in Hall of Heroes")

        # Initialize Boss Quests
        init_boss_quests()

    except Exception as e:
        print(f"⚠️ Error creating default groups: {e}")
        db.session.rollback()

def init_boss_quests():
    """Create persistent Boss Quest instances for the Quest Board with scalable levels"""
    
    # Boss Base Definitions
    boss_bases = [
        {
            "id": "client_v1",
            "name": "Difficult Client (v1)",
            "description": "A high-stakes negotiation with a client who refuses to pay. Test negotiation and boundaries.",
            "goal": "Secure full payment without burning the bridge.",
            "base_xp": 20, "base_reward": "Satisfied Client Title", "risk_base": "Loss of reputation"
        },
        {
            "id": "new_client",
            "name": "New Client",
            "description": "A massive potential account with a extremely tough procurement officer. Test tough negotiation and problem-solving sales skills.",
            "goal": "Close the deal with favorable terms and solve their logistics bottleneck.",
            "base_xp": 40, "base_reward": "Preferred Partner Status", "risk_base": "Loss of potential revenue"
        },
        {
            "id": "supplier_v1",
            "name": "New Supplier",
            "description": "Secure a mission-critical component from a skeptical supplier. Build trust and technical rapport.",
            "goal": "Unlock the supply chain.",
            "base_xp": 30, "base_reward": "Supply Chain Unlocked", "risk_base": "Project delay"
        },
        {
            "id": "supplier_v2",
            "name": "Difficult Supplier",
            "description": "Supplier acquired by competitor. Leverage moats to stay indispensable.",
            "goal": "Maintain your resource advantage.",
            "base_xp": 50, "base_reward": "Resource Moat Title", "risk_base": "Loss of raw materials"
        },
        {
            "id": "mutiny",
            "name": "Mutiny of Team Member",
            "description": "One of the Big 6 is being poached. Secure loyalty with trust topologies.",
            "goal": "Unbreakable loyalty.",
            "base_xp": 70, "base_reward": "Unbreakable Loyalty", "risk_base": "Loss of a Big 6 NPC"
        },
        {
            "id": "recruitment",
            "name": "New Team Member",
            "description": "Recruit a high-value architect while filtering saboteurs.",
            "goal": "Successfully recruit a loyal architect.",
            "base_xp": 40, "base_reward": "New Architect NPC", "risk_base": "Hiring a saboteur"
        },
        {
            "id": "red_tape",
            "name": "Red Tape Official",
            "description": "Bureaucracy threatening your Dwell Time. Gain sovereign status.",
            "goal": "Obtain Legal Immunity.",
            "base_xp": 80, "base_reward": "Sovereign Status", "risk_base": "Project Shutdown"
        },
        {
            "id": "family",
            "name": "Difficult Family Member",
            "description": "Family member sabotaging focus. Set emotional boundaries.",
            "goal": "Establish Legacy Clarity.",
            "base_xp": 60, "base_reward": "Legacy Clarity", "risk_base": "Emotional Debuff"
        },
        {
            "id": "agitator",
            "name": "Community Agitator",
            "description": "Rival spreading rumors. Use social engineering.",
            "goal": "Reclaim public reputation.",
            "base_xp": 90, "base_reward": "District Founder Title", "risk_base": "Public Exile"
        },
        {
            "id": "spouse",
            "name": "Difficult Spouse",
            "description": "The Ultimate Covenant. Partner at breaking point. Salvage relationship.",
            "goal": "Forge a Dynasty.",
            "base_xp": 150, "base_reward": "Dynasty Founder Status", "risk_base": "Divorce / Game Over"
        }
    ]

    quest_board = Group.query.filter_by(group_name='Quest Board').first()
    
    # Generate 5 levels for each boss
    for base in boss_bases:
        for lvl in range(1, 6):
            quest_name = f"Boss: {base['name']} [Level {lvl}]"
            
            # Skip if already exists
            if Quest.query.filter_by(name=quest_name).first():
                continue
            
            # Scale XP, Rewards, and Risk
            xp_reward = base['base_xp'] * lvl
            scaled_reward = f"{base['base_reward']} (Lvl {lvl})"
            if lvl >= 3:
                scaled_reward += f" + Rare Item: {base['id']}_artifact_v{lvl}"
            
            risk_desc = f"CRITICAL RISK: {base['risk_base']} (Severity: {lvl}/5)"
            
            description = f"{base['description']}\n\n{risk_desc}"
            
            new_boss = Quest(
                id=str(uuid.uuid4()),
                name=quest_name,
                description=description,
                start_location="Current Location (Trigger Event)",
                end_goal=base['goal'],
                requirements=json.dumps([f"Integrity Score > {lvl * 10}"]),
                difficulty="BOSS",
                created_by='QUEST',
                reward=scaled_reward
            )
            db.session.add(new_boss)
            
            # Post to Quest Board
            if quest_board:
                quest_data = {
                    "title": quest_name,
                    "description": description,
                    "start_location": "Current Location (Trigger Event)",
                    "end_goal": base['goal'],
                    "xp": xp_reward,
                    "requirements": [f"Integrity Score > {lvl * 10}"],
                    "source": "boss_instance",
                    "difficulty": "BOSS",
                    "boss_level": lvl
                }
                msg = Message(
                    msg_id=str(uuid.uuid4()),
                    sender_id='QUEST',
                    chat_id=quest_board.id,
                    content=f"[QUEST_DATA] {json.dumps(quest_data)}"
                )
                db.session.add(msg)
    
    db.session.commit()
    print(f"✅ Initialized Scalable Boss Instances (Lvl 1-5) on Quest Board")

    # New Regional Scale-Based Quests (Hierarchy: Village to Country)
    scale_configs = [
        {"lvl": 1, "scale": "Village", "xp": 250, "reward": "Village Guardian"},
        {"lvl": 2, "scale": "Town", "xp": 750, "reward": "Town Protector"},
        {"lvl": 3, "scale": "City", "xp": 2000, "reward": "City Sentinel"},
        {"lvl": 4, "scale": "County/Province", "xp": 5000, "reward": "Province Warden"},
        {"lvl": 5, "scale": "Country", "xp": 15000, "reward": "Sovereign Liberator"}
    ]

    for cfg in scale_configs:
        lvl = cfg['lvl']
        unit = cfg['scale']
        quest_name = f"Boss: Save a {unit} [Level {lvl}]"
        
        # Skip if already exists
        if Quest.query.filter_by(name=quest_name).first():
            continue
            
        xp_reward = cfg['xp']
        scaled_reward = f"{cfg['reward']} status"
        if lvl >= 3:
            scaled_reward += f" + Rare Item: sovereign_emblem_v{lvl}"
        if lvl == 5:
            scaled_reward += " + GLOBAL TITAN STATUS"
        
        risk_desc = f"CRITICAL RISK: Complete Systemic Collapse of the {unit} (Severity: {lvl}/5)"
        
        description = (
            f"The {unit} is facing an existential crisis. Challenges relate to regional systemic issues "
            f"including infrastructure, security, and socio-economic stability. "
        )
        if lvl == 5:
            description += ("\n\n**EXTREME DIFFICULTY:** This is a TITAN-level simulation of national-scale complex problems. "
                            "Requires real-world tactical logic and deep geo-spatial awareness. Failure is permanent.")
        
        description += f"\n\n{risk_desc}"
        
        new_boss = Quest(
            id=str(uuid.uuid4()),
            name=quest_name,
            description=description,
            start_location="Current Location (Trigger Event)",
            end_goal=f"Stabilize and secure the {unit} against all threats.",
            requirements=json.dumps([f"Integrity Score > {lvl * 20}"]),
            difficulty="BOSS",
            created_by='QUEST',
            reward=scaled_reward
        )
        db.session.add(new_boss)
        
        # Post to Quest Board
        if quest_board:
            quest_data = {
                "title": quest_name,
                "description": description,
                "start_location": "Current Location (Trigger Event)",
                "end_goal": f"Stabilize and secure the {unit} against all threats.",
                "xp": xp_reward,
                "requirements": [f"Integrity Score > {lvl * 20}"],
                "source": "boss_instance",
                "difficulty": "BOSS",
                "boss_level": lvl
            }
            msg = Message(
                msg_id=str(uuid.uuid4()),
                sender_id='QUEST',
                chat_id=quest_board.id,
                content=f"[QUEST_DATA] {json.dumps(quest_data)}"
            )
            db.session.add(msg)
    
    db.session.commit()
    print(f"✅ Initialized Regional Scale Quests (Village -> Country)")

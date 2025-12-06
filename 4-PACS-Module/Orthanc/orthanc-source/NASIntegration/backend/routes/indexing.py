"""
Indexing blueprint: handles starting/stopping/indexing status for NAS indexing operations.
Extracted from nas_core.py to improve maintainability.
"""
import logging
import os
from datetime import datetime
from flask import Blueprint, request, jsonify
import socket

# Import NAS configuration - try relative import first, then absolute
try:
    from nas_config.nas_configuration import get_nas_config, get_active_nas_path
except ImportError:
    from backend.nas_config.nas_configuration import get_nas_config, get_active_nas_path

logger = logging.getLogger(__name__)

indexing_bp = Blueprint('nas_indexing', __name__)

# Simple in-memory indexing state for frontend polling (compat/demo)
indexing_state = {
    'state': 'idle',
    'progress': 0,
    'details': 'Idle',
    'started_at': None
}

# Try to import helper to get canonical metadata DB path used by the application
try:
    from backend.metadata_db import get_metadata_db_path
except Exception:
    try:
        from metadata_db import get_metadata_db_path
    except Exception:
        def get_metadata_db_path():
            # Fallback to a safe metadata DB path inside backend/orthanc-index
            base = os.path.dirname(os.path.dirname(__file__))  # backend/
            fallback = os.path.abspath(os.path.join(base, 'orthanc-index', 'pacs_metadata.db'))
            return fallback


@indexing_bp.route('/indexing/start', methods=['POST'])
def start_indexing():
    """Start indexing process"""
    try:
        data = request.get_json() or {}
        share_path = data.get('share_path') or data.get('sharePath') or data.get('path', '/nas/dicom/')
        username = data.get('username')
        # Note: password omitted from logs for security
        
        # Update state immediately for frontend feedback
        indexing_state['state'] = 'indexing'
        indexing_state['progress'] = 0
        indexing_state['details'] = f"Indexing started for {share_path}"
        # Record start time and process id so callers can detect which process owns the state
        indexing_state['started_at'] = datetime.utcnow().isoformat() + 'Z'
        try:
            indexing_state['pid'] = os.getpid()
        except Exception:
            indexing_state['pid'] = None
        logger.info(f"🔥 INDEXING STATE SET TO: {indexing_state}")
        logger.info(f"Real indexing started for share: {share_path}")
        
        # Check if caller wants to write to Orthanc internal index (risky) or safe metadata DB
        use_internal = os.environ.get('USE_ORTHANC_INTERNAL_INDEX', 'false').lower() == 'true'
        if use_internal:
            logger.warning("⚠️ USE_ORTHANC_INTERNAL_INDEX=true - will attempt to merge into Orthanc internal index after indexing completes")
        else:
            logger.info("✅ USE_ORTHANC_INTERNAL_INDEX=false - indexing will use safe metadata DB (pacs_metadata.db)")

        # Start real indexing in background thread
        import threading
        import sys
        import shutil
        import time
        
        # Add parent directory to path to find nas_patient_indexer
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        # Ensure canonical metadata DB directory exists (we are using Orthanc internal index per user request)
        try:
            canonical_db = get_metadata_db_path()
            canonical_dir = os.path.dirname(canonical_db)
            os.makedirs(canonical_dir, exist_ok=True)
            # Move legacy DBs if present
            legacy_candidates = [
                os.path.join(os.path.dirname(__file__), '..', 'nas_patient_index.db'),
                os.path.join(os.path.dirname(__file__), '..', 'pacs_index.db'),
                os.path.join(os.path.dirname(__file__), '..', 'medical_index.db'),
            ]
            backup_dir = os.path.join(canonical_dir, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            for legacy in legacy_candidates:
                try:
                    legacy_path = os.path.abspath(os.path.normpath(legacy))
                    if os.path.exists(legacy_path):
                        dest = os.path.join(backup_dir, f"{os.path.basename(legacy_path)}.{timestamp}.bak")
                        shutil.move(legacy_path, dest)
                        logger.info(f"Moved legacy DB {legacy_path} -> {dest}")
                except Exception as e:
                    logger.debug(f"Could not move legacy DB {legacy}: {e}")
        except Exception:
            # Non-fatal; proceed without backup
            pass
        
        def run_real_indexing():
            """Run actual NAS indexing in background"""
            try:
                from nas_patient_indexer import NASPatientIndexer
                import sqlite3
                # Use the share path provided by the frontend request (share_path)
                # Fallback to configured NAS path if none provided
                if not share_path:
                    nas_path = get_active_nas_path()
                    logger.info(f"📍 Using configured NAS path: {nas_path}")
                else:
                    nas_path = share_path
                nas_path = str(nas_path).strip()

                # Determine which DB to use based on USE_ORTHANC_INTERNAL_INDEX flag
                try:
                    canonical_index = get_metadata_db_path()  # typically orthanc-index/pacs_metadata.db
                    canonical_dir = os.path.dirname(canonical_index)

                    # If the caller requested writing to Orthanc internals, prefer the 'index' file inside the same dir
                    if use_internal:
                        orthanc_index_candidate = os.path.join(canonical_dir, 'index')
                        if os.path.exists(orthanc_index_candidate):
                            logger.info(f"🔎 USE_ORTHANC_INTERNAL_INDEX enabled - will target Orthanc internal index at {orthanc_index_candidate}")
                            canonical_index = orthanc_index_candidate
                        else:
                            logger.warning(f"⚠️ USE_ORTHANC_INTERNAL_INDEX requested but Orthanc 'index' file not found at {orthanc_index_candidate}; falling back to {canonical_index}")
                    else:
                        # USE_ORTHANC_INTERNAL_INDEX=false: use safe pacs_metadata.db
                        safe_db = os.path.join(canonical_dir, 'pacs_metadata.db')
                        logger.info(f"✅ USE_ORTHANC_INTERNAL_INDEX=false - will use safe metadata DB: {safe_db}")
                        canonical_index = safe_db
                    
                    timestamp = time.strftime('%Y%m%d_%H%M%S')
                    working_db = os.path.join(canonical_dir, f'index_working_{timestamp}.db')

                    logger.info(f"🔁 Creating working DB copy from Orthanc index: {canonical_index} -> {working_db}")

                    # Open source in read-only mode and backup to working DB file
                    try:
                        src = sqlite3.connect(f'file:{canonical_index}?mode=ro', uri=True)
                        dest = sqlite3.connect(working_db)
                        with dest:
                            src.backup(dest)
                        src.close()
                        dest.close()
                        logger.info(f"✅ Working DB copy created: {working_db}")
                    except Exception as e:
                        logger.error(f"❌ Failed to create working DB copy from {canonical_index}: {e}")
                        # Fall back to using canonical_index path directly (risky)
                        working_db = canonical_index

                except Exception as e:
                    logger.error(f"Error preparing working DB: {e}")
                    working_db = None

                # Initialize indexer to use the working DB (if available) to avoid writing to live Orthanc index
                if working_db:
                    indexer = NASPatientIndexer(nas_path=nas_path, db_path=working_db)
                else:
                    # As a last resort, proceed with default behavior (may write to canonical path)
                    indexer = NASPatientIndexer(nas_path=nas_path)

                logger.info(f"🚀 Starting real NAS patient indexing from {nas_path} (db={indexer.db_path})...")
                
                # Update state to show real indexing
                indexing_state['details'] = f"Real indexing in progress from {nas_path}"
                indexing_state['progress'] = 5
                # Ensure pid/stamp are present for diagnostics
                try:
                    indexing_state['pid'] = os.getpid()
                    indexing_state['started_at'] = datetime.utcnow().isoformat() + 'Z'
                except Exception:
                    pass
                
                # Run indexing with reasonable worker count
                indexer.run_full_index(max_workers=2)  # Use 2 workers to avoid database locks
                
                # Merge working DB back into canonical index to persist results
                try:
                    if working_db and working_db != canonical_index:
                        if use_internal:
                            # Merging into Orthanc internal index - extra safety checks
                                    if os.path.basename(canonical_index).lower() == 'index':
                                        # Ensure Orthanc is NOT running before attempting to write its internal index
                                        orthanc_host = os.environ.get('ORTHANC_HOST', '127.0.0.1')
                                        try:
                                            orthanc_port = int(os.environ.get('ORTHANC_PORT', '8042'))
                                        except Exception:
                                            orthanc_port = 8042

                                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                        s.settimeout(1.0)
                                        try:
                                            s.connect((orthanc_host, orthanc_port))
                                            s.close()
                                            logger.error(f"Refusing to merge into Orthanc internal index because Orthanc appears reachable at {orthanc_host}:{orthanc_port}. Stop Orthanc before enabling USE_ORTHANC_INTERNAL_INDEX.")
                                        except (ConnectionRefusedError, socket.timeout, OSError):
                                            # Orthanc not reachable - safe to merge
                                            logger.info(f"🔁 Merging working DB {working_db} -> Orthanc internal index {canonical_index}")
                                            try:
                                                src = sqlite3.connect(f'file:{working_db}?mode=ro', uri=True)
                                                dest = sqlite3.connect(canonical_index)
                                                with dest:
                                                    src.backup(dest)
                                                src.close()
                                                dest.close()
                                                logger.info(f"✅ Merged working DB into Orthanc internal index: {canonical_index}")
                                            except Exception as merge_err:
                                                logger.error(f"❌ Failed to merge working DB into Orthanc internal index: {merge_err}")
                                    else:
                                        logger.warning(f"⚠️ Canonical index {canonical_index} does not look like Orthanc internal 'index' file; skipping merge")
                        else:
                            # Safe metadata DB - just overwrite it
                            logger.info(f"🔁 Replacing safe metadata DB {canonical_index} with working DB {working_db}")
                            try:
                                src = sqlite3.connect(f'file:{working_db}?mode=ro', uri=True)
                                dest = sqlite3.connect(canonical_index)
                                with dest:
                                    src.backup(dest)
                                src.close()
                                dest.close()
                                logger.info(f"✅ Updated safe metadata DB: {canonical_index}")
                            except Exception as merge_err:
                                logger.error(f"❌ Failed to update safe metadata DB: {merge_err}")
                    else:
                        logger.info("ℹ️ No working DB merge required (working_db == canonical_index)")
                except Exception as e:
                    logger.error(f"❌ Error during post-index merge: {e}")

                # Update state on completion
                indexing_state['state'] = 'completed'
                indexing_state['progress'] = 100
                indexing_state['details'] = "Real NAS indexing completed successfully"
                logger.info("✅ Real NAS indexing completed successfully")
                
            except Exception as e:
                logger.error(f"❌ Real NAS indexing failed: {e}")
                indexing_state['state'] = 'error'
                indexing_state['details'] = f"Indexing failed: {str(e)}"
        
        # Start indexing thread
        threading.Thread(target=run_real_indexing, daemon=True).start()
        
        return jsonify({
            'success': True,
            'message': 'Real DICOM indexing started',
            'status': 'indexing',
            'details': 'Background indexing thread started for NAS DICOM files'
        })
    except Exception as e:
        # Log full traceback to help debug scope errors like UnboundLocalError
        logger.exception(f"Start indexing error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


@indexing_bp.route('/indexing/stop', methods=['POST'])
def stop_indexing():
    """Stop indexing process"""
    try:
        indexing_state['state'] = 'idle'
        indexing_state['progress'] = 100
        indexing_state['details'] = 'Stopped by user'
        indexing_state['started_at'] = None
        return jsonify({
            'success': True,
            'message': 'Indexing stopped',
            'status': 'idle'
        })
    except Exception as e:
        logger.error(f"Stop indexing error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


@indexing_bp.route('/start-indexing', methods=['POST'])
def start_indexing_compat():
    """Compatibility endpoint: /api/nas/start-indexing"""
    return start_indexing()


@indexing_bp.route('/indexing/status', methods=['GET'])
def indexing_status():
    """Return indexing status for frontend polling"""
    logger.info("🚨 INDEXING STATUS ENDPOINT CALLED - MAIN ENDPOINT")
    try:
        # Check if real indexing is actually happening by looking for the database
        real_indexing_active = False
        patient_count = 0
        
        # First check if we have a running indexing state from the start endpoint
        if indexing_state['state'] == 'indexing':
            logger.info(f"🔥 Indexing state shows active: {indexing_state}")
            real_indexing_active = True
            
        # Also check if we started indexing recently (within last 10 minutes)
        if indexing_state.get('started_at'):
            try:
                if isinstance(indexing_state['started_at'], str):
                    # Parse string datetime
                    started_time = datetime.fromisoformat(indexing_state['started_at'].replace('Z', '+00:00'))
                else:
                    started_time = indexing_state['started_at']
                
                time_since_start = (datetime.utcnow() - started_time).total_seconds()
                logger.info(f"⏱️ Indexing started {time_since_start:.1f} seconds ago")
                
                if time_since_start < 600:  # Started within 10 minutes
                    real_indexing_active = True
                    logger.info(f"✅ Recent indexing start detected - assuming still active")
            except Exception as e:
                logger.debug(f"Error parsing start time: {e}")
        
        try:
            import sqlite3
            
            # Prefer the canonical metadata DB path used by the app
            canonical_db = None
            try:
                canonical_db = get_metadata_db_path()
            except Exception:
                canonical_db = None

            db_paths = [p for p in ([canonical_db] if canonical_db else []) + [r"\\TRUENAS\Medical_Images\medical_index.db", os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'nas_patient_index.db')), os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'medical_index.db')), os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'patient_index.db'))] if p]

            for db_path in db_paths:
                try:
                    if os.path.exists(db_path):
                        # Check if file was modified recently (within last 2 minutes for more tolerance)
                        mod_time = os.path.getmtime(db_path)
                        current_time = datetime.utcnow().timestamp()
                        time_since_mod = current_time - mod_time
                        logger.info(f"📊 Database {db_path}: modified {time_since_mod:.1f} seconds ago")

                        if time_since_mod < 120:  # Modified within 2 minutes
                            real_indexing_active = True
                            logger.info(f"✅ Database activity detected - indexing is active")

                        # Try to open DB in read-only mode to avoid interfering with live services
                        try:
                            conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=5)
                        except Exception:
                            conn = sqlite3.connect(db_path, timeout=5)

                        with conn:
                            cursor = conn.cursor()
                            # Check if we have the patient_studies table
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patient_studies'")
                            if cursor.fetchone():
                                # Count total studies (what PACS users care about)
                                cursor.execute("SELECT COUNT(*) FROM patient_studies")
                                count_result = cursor.fetchone()
                                if count_result and count_result[0]:
                                    patient_count = count_result[0]
                                    logger.info(f"📊 Found {patient_count} studies in database")
                                    break
                except Exception:
                    continue
                    
        except Exception:
            pass
        
        # Only update state if we detect ACTIVE indexing - don't override existing state
        if real_indexing_active:
            # If transitioning from non-indexing to indexing, record start time
            if indexing_state['state'] != 'indexing':
                indexing_state['started_at'] = datetime.utcnow().isoformat() + 'Z'
                
            indexing_state['state'] = 'indexing'
            # 🚀 Try to get REAL-TIME progress from indexing process
            try:
                import json
                import time
                progress_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'indexing_progress.json')
                
                if os.path.exists(progress_file) and (time.time() - os.path.getmtime(progress_file)) < 30:
                    with open(progress_file, 'r') as f:
                        progress = json.load(f)
                    
                    completed = progress.get('completed', 0)
                    total = progress.get('total', 7267)
                    rate = progress.get('rate', 0)
                    current_folder = progress.get('current_folder', 'Processing...')
                    
                    # Use REAL progress
                    indexing_state['progress'] = min(int((completed / total) * 100), 95) if total > 0 else 10
                    
                    # Calculate real ETA
                    remaining = max(0, total - completed)
                    eta_seconds = remaining / rate if rate > 0 else 0
                    
                    if eta_seconds > 3600:
                        eta_hours = int(eta_seconds / 3600)
                        eta_minutes = int((eta_seconds % 3600) / 60)
                        eta_text = f"ETA: ~{eta_hours}h {eta_minutes}m"
                    elif eta_seconds > 60:
                        eta_minutes = int(eta_seconds / 60)
                        eta_text = f"ETA: ~{eta_minutes} minutes"  
                    else:
                        eta_text = "ETA: <1 minute" if eta_seconds > 0 else "Nearly done"
                    
                    rate_per_hour = rate * 3600
                    indexing_state['details'] = f"📊 Processing: {completed:,}/{total:,} folders • {rate_per_hour:.0f}/hour • {eta_text}"
                    logger.info(f"✅ REAL-TIME: {completed}/{total} folders @ {rate:.2f}/sec")
                else:
                    raise Exception("No recent progress data")
                    
            except Exception as e:
                logger.debug(f"Using fallback progress calculation: {e}")
                indexing_state['progress'] = min(int((patient_count / 7267) * 100), 95) if patient_count > 0 else 10
            
            # Create more human-friendly progress details
            estimated_total = 7267
            completion_percentage = min(int((patient_count / estimated_total) * 100), 95)
            remaining = max(0, estimated_total - patient_count)
            
            # Calculate estimated time based on current progress
            if indexing_state.get('started_at'):
                try:
                    start_time = indexing_state['started_at']
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    
                    elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
                    if patient_count > 0 and elapsed_seconds > 0:
                        rate_per_second = patient_count / elapsed_seconds
                        eta_seconds = remaining / rate_per_second if rate_per_second > 0 else 0
                        eta_minutes = int(eta_seconds / 60)
                        
                        if eta_minutes > 60:
                            eta_hours = eta_minutes // 60
                            eta_minutes = eta_minutes % 60
                            eta_text = f"~{eta_hours}h {eta_minutes}m remaining"
                        elif eta_minutes > 0:
                            eta_text = f"~{eta_minutes} minutes remaining"
                        else:
                            eta_text = "Nearly complete"
                    else:
                        eta_text = "Calculating time remaining..."
                except:
                    eta_text = ""
            else:
                eta_text = ""
            
            # Calculate processing rate and ETA
            if indexing_state.get('started_at'):
                try:
                    start_time = indexing_state['started_at']
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    
                    elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
                    if elapsed_seconds > 0:
                        rate_per_minute = (patient_count / elapsed_seconds) * 60
                        estimated_total = 7267  # Total expected studies
                        remaining = max(0, estimated_total - patient_count)
                        eta_seconds = remaining / (rate_per_minute / 60) if rate_per_minute > 0 else 0
                        
                        if eta_seconds > 3600:  # More than 1 hour
                            eta_hours = int(eta_seconds / 3600)
                            eta_minutes = int((eta_seconds % 3600) / 60)
                            eta_text = f"ETA: ~{eta_hours}h {eta_minutes}m"
                        elif eta_seconds > 60:  # More than 1 minute
                            eta_minutes = int(eta_seconds / 60)
                            eta_text = f"ETA: ~{eta_minutes} minutes"
                        else:
                            eta_text = "ETA: <1 minute"
                        
                        indexing_state['details'] = f"📊 Indexing: {patient_count:,} studies • Rate: {rate_per_minute:.1f}/min • {eta_text}"
                    else:
                        indexing_state['details'] = f"📊 Indexing PACS studies: {patient_count:,} studies indexed"
                except Exception as e:
                    logger.debug(f"ETA calculation error: {e}")
                    indexing_state['details'] = f"📊 Indexing PACS studies: {patient_count:,} studies indexed • {eta_text}"
            else:
                indexing_state['details'] = f"📊 Indexing PACS studies: {patient_count:,} studies indexed"
            
        # Only mark as completed if we're currently idle AND have substantial data  
        elif indexing_state['state'] == 'idle' and patient_count > 1000:
            indexing_state['state'] = 'completed'
            indexing_state['progress'] = 100
            indexing_state['details'] = f"✅ Completed: {patient_count:,} patients successfully indexed"
            
        # If state is already 'indexing' and we don't detect active changes, keep it as indexing
        elif indexing_state['state'] == 'indexing':
            # Keep current progress, just update details with better formatting
            estimated_total = 7267
            completion_percentage = min(int((patient_count / estimated_total) * 100), 95)
            indexing_state['progress'] = completion_percentage
            indexing_state['details'] = f"� Discovered {patient_count:,} patients • Scanning continues..."
        
        logger.info(f"🔍 Status check - Real active: {real_indexing_active}, Patient count: {patient_count}, State: {indexing_state['state']}")
        
        # If indexing is running, check if we can get real progress from the database
        if indexing_state['state'] == 'indexing':
            try:
                import sqlite3
                
                # Try to get real patient count from database
                patient_count = 0
                db_paths = [
                    r"\\TRUENAS\Medical_Images\medical_index.db",
                    "medical_index.db", 
                    "patient_index.db"
                ]
                
                for db_path in db_paths:
                    try:
                        if os.path.exists(db_path):
                            with sqlite3.connect(db_path, timeout=5) as conn:
                                cursor = conn.cursor()
                                cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies")
                                count_result = cursor.fetchone()
                                if count_result and count_result[0]:
                                    patient_count = count_result[0]
                                    break
                    except Exception:
                        continue
                
                if patient_count > 0:
                    # Estimate progress based on patient count (we know there are ~7267 total folders)
                    estimated_total = 7267
                    real_progress = min(int((patient_count / estimated_total) * 100), 99)
                    indexing_state['progress'] = max(indexing_state['progress'], real_progress)
                    indexing_state['details'] = f"✅ {patient_count} patients indexed from NAS"
                
            except Exception as e:
                logger.debug(f"Could not get real indexing progress: {e}")
                # Fall back to time-based simulation if database check fails
                if indexing_state['started_at']:
                    elapsed = (datetime.utcnow() - indexing_state['started_at']).total_seconds()
                    # Slower progress: 2% per second for more realistic indexing time
                    prog = min(95, int(elapsed * 2))  # Cap at 95% until real completion
                    indexing_state['progress'] = max(indexing_state['progress'], prog)
        
        # Map backend states to frontend-expected states
        state_mapping = {
            'indexing': 'running',
            'completed': 'completed',
            'idle': 'idle',
            'error': 'error'
        }
        
        frontend_state = state_mapping.get(indexing_state['state'], 'idle')
        
        response_data = {
            'success': True,
            'status': {
                'state': frontend_state,
                'progress': indexing_state['progress'],
                'pid': indexing_state.get('pid'),
                'details': indexing_state['details']
            }
        }
        
        logger.info(f"🔄 Status API response: {response_data}")
        logger.info(f"🔄 Frontend should see: state='{frontend_state}', progress={indexing_state['progress']}")
        logger.info(f"🔄 Original backend state was: '{indexing_state['state']}'")
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Indexing status error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


def get_indexing_status_safe():
    """Get indexing status in a safe format for dashboard"""
    try:
        # Get real patient count from database if available
        patient_count = 0
        last_update = None
        
        try:
            import sqlite3
            
            # Try to connect to the patient database
            db_paths = [
                r"\\TRUENAS\Medical_Images\medical_index.db",
                "medical_index.db", 
                "patient_index.db"
            ]
            
            for db_path in db_paths:
                try:
                    if os.path.exists(db_path):
                        with sqlite3.connect(db_path, timeout=5) as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies")
                            count_result = cursor.fetchone()
                            if count_result and count_result[0]:
                                patient_count = count_result[0]
                                
                                # Get last update
                                cursor.execute("SELECT MAX(created_at) FROM patient_studies")
                                update_result = cursor.fetchone()
                                if update_result and update_result[0]:
                                    last_update = update_result[0]
                                break
                except Exception:
                    continue
                    
        except Exception:
            pass
        
        # Determine status based on state and patient count
        if patient_count > 0:
            status_details = f"✅ {patient_count} patients indexed and available"
            status_state = 'completed' if indexing_state['state'] != 'indexing' else indexing_state['state']
            status_progress = 100 if patient_count > 0 and indexing_state['state'] != 'indexing' else indexing_state['progress']
        else:
            status_details = indexing_state.get('details', 'No patients indexed yet')
            status_state = indexing_state['state']
            status_progress = indexing_state['progress']
        
        return {
            'total_patients': patient_count,
            'is_running': indexing_state['state'] == 'indexing',
            'progress': status_progress,
            'details': status_details,
            # Frontend expects 'last_updated' (not 'last_update')
            'last_updated': last_update,
            'state': status_state,
            'source': 'database' if patient_count > 0 else 'memory',
            # Provide basic auto-indexing info so dashboard can show last_check and monitoring status
            'auto_indexing': {
                'monitoring': False,
                'mounted_shares': 0,
                'last_check': last_update
            }
        }
        
    except Exception as e:
        return {
            'total_patients': 0,
            'is_running': False,
            'progress': 0,
            'details': f'Status error: {str(e)}',
            'state': 'error',
            'source': 'error'
        }


# ============================================================================
# NAS Configuration Management Endpoints
# ============================================================================

@indexing_bp.route('/config/active', methods=['GET'])
def get_active_nas_config():
    """Get the currently active NAS configuration"""
    try:
        config = get_nas_config()
        active_config = config.get_active_nas_config()
        active_path = config.get_active_nas_path()
        
        return jsonify({
            'success': True,
            'path': active_path,
            'description': active_config.get('description', ''),
            'modalities': active_config.get('modalities', []),
            'enabled': active_config.get('enabled', False),
            'source': config.config.get('source', 'unknown')
        })
    except Exception as e:
        logger.error(f"Error getting active NAS config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@indexing_bp.route('/config/all', methods=['GET'])
def get_all_nas_configs():
    """Get all available NAS configurations"""
    try:
        config = get_nas_config()
        all_configs = config.get_nas_configs()
        active_alias = config.config.get('active_alias', 'unknown')
        
        result = {}
        for alias, cfg in all_configs.items():
            result[alias] = {
                'path': cfg.get('path', ''),
                'description': cfg.get('description', ''),
                'modalities': cfg.get('modalities', []),
                'enabled': cfg.get('enabled', False),
                'is_active': alias == active_alias
            }
        
        return jsonify({
            'success': True,
            'configs': result,
            'active_alias': active_alias
        })
    except Exception as e:
        logger.error(f"Error getting all NAS configs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@indexing_bp.route('/config/switch', methods=['POST'])
def switch_nas_config():
    """Switch to a different NAS configuration"""
    try:
        data = request.get_json() or {}
        alias = data.get('alias')
        
        if not alias:
            return jsonify({
                'success': False,
                'error': 'Missing "alias" parameter'
            }), 400
        
        config = get_nas_config()
        if config.set_active_nas(alias):
            # Get the updated path after switching
            new_path = get_active_nas_path()
            new_config = config.get_active_nas_config()
            
            logger.info(f"✅ Switched NAS configuration to: {alias} ({new_path})")
            
            return jsonify({
                'success': True,
                'message': f'Switched to {alias}',
                'new_path': new_path,
                'new_config': new_config
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to switch to {alias}'
            }), 500
    
    except Exception as e:
        logger.error(f"Error switching NAS config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@indexing_bp.route('/config/check-accessibility', methods=['GET'])
def check_nas_accessibility():
    """Check if the active NAS is accessible"""
    try:
        config = get_nas_config()
        nas_path = config.get_active_nas_path()
        
        if os.path.exists(nas_path):
            try:
                # Try to list first few items
                items = []
                for item in os.listdir(nas_path)[:5]:
                    items.append(item)
                
                total_items = len(os.listdir(nas_path))
                
                return jsonify({
                    'success': True,
                    'accessible': True,
                    'path': nas_path,
                    'total_items': total_items,
                    'sample_items': items
                })
            except Exception as e:
                logger.warning(f"Could not list NAS contents: {e}")
                return jsonify({
                    'success': True,
                    'accessible': True,
                    'path': nas_path,
                    'warning': str(e)
                })
        else:
            return jsonify({
                'success': True,
                'accessible': False,
                'path': nas_path,
                'error': 'NAS path does not exist or is not accessible'
            })
    
    except Exception as e:
        logger.error(f"Error checking NAS accessibility: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

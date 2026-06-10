"""
SDOH Document Mixin
===================
Provides document indexing, guidance, and extraction methods for the SDOH agent.
"""

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

# Import the PatientDocumentIndexer from the main module
from backend.sdoh_patient_index import PatientDocumentIndexer, _win_isdir

class SDOHDocumentMixin:
    """Mixin providing document indexing and guidance methods."""
    
    def _extract_candidate_path(self, text: str) -> Optional[str]:
        """Extract a file system path from user input."""
        if not text:
            return None
        # Match Windows drive paths (X:\, C:\, etc.) - allow spaces in paths
        # Pattern: Drive letter + colon + backslash, then any chars including spaces until we hit a quote or pipe
        m = re.search(r'[A-Za-z]:\\(?:[^"\'|]+\\)*[^"\'|]*', text)
        if m:
            path = m.group(0).strip()
            # Clean up any trailing quotes or pipes that might have been captured
            path = path.rstrip("\"'|")
            return path
        # Match UNC paths
        m = re.search(r'\\\\[^\\\s"\'|]+', text)
        if m:
            return m.group(0)
        return None
    
    def _wants_tool_execution(self, text: str) -> bool:
        """Check if user wants immediate tool execution."""
        if not text:
            return False
        text_lower = text.lower()
        return any(term in text_lower for term in [
            'run now', 'yes', 'do it', 'execute now', 'scan now',
            'index now', 'do it now', 'execute', 'start now', 'run'
        ])
    
    def _is_direct_indexing_command(self, text: str) -> bool:
        """Check if this is a direct indexing command."""
        if not text:
            return False
        text_lower = text.lower()
        return 'index' in text_lower and any(term in text_lower for term in [
            'folder', 'drive', 'dicom', 'scan', 'start'
        ])
    
    def _topic(self, text: str) -> str:
        """Determine the topic of the user input."""
        if not text:
            return 'general'
        text_lower = text.lower()
        if 'siim' in text_lower and ('ingest' in text_lower or 'status' in text_lower or 'hackathon' in text_lower):
            return 'siim_ingest'
        if any(t in text_lower for t in ['index', 'scan', 'dicom', 'folder', 'drive']):
            return 'index_records'
        if any(t in text_lower for t in ['document', 'report', 'show me', 'what do i have', 'list', 'patient']):
            return 'show_documents'
        if any(t in text_lower for t in ['history pack', 'share', 'prepare']):
            return 'history_pack'
        return 'general'
    
    def _query_vault_index_for_folder(self, folder_path: str) -> Dict[str, Any]:
        """Query the SQLite health graph database for files matching a folder path."""
        vault_db_path = r'C:\Users\Admin\.openclaw\vault\index\master_health_graph.db'
        
        if not os.path.exists(vault_db_path):
            return {"count": 0, "error": "Vault SQLite database not found"}
        
        try:
            from backend.health_graph_schema import HealthGraphSchema
            db = HealthGraphSchema(vault_db_path)
            
            # Get all files and filter by folder path
            normalized_folder = folder_path.replace('\\\\', '\\').lower()
            
            cursor = db.conn.cursor()
            cursor.execute('SELECT file_path, modality FROM files')
            all_files = cursor.fetchall()
            
            matching = [f for f in all_files 
                       if f['file_path'].replace('\\\\', '\\').lower().startswith(normalized_folder)]
            
            # Get modalities
            modalities = {}
            for f in matching:
                mod = f['modality'] or 'unknown'
                modalities[mod] = modalities.get(mod, 0) + 1
            
            db.close()
            
            return {
                "count": len(matching),
                "modalities": modalities,
                "sample": matching[:5] if matching else [],
            }
        except Exception as e:
            return {"count": 0, "error": str(e)}
    
    def _build_index_guidance(self, user_input: str, user_alias: str = 'Patient') -> Dict[str, Any]:
        """Trigger or explain the local document index scan."""
        indexer = self._get_indexer()
        
        candidate_path = self._extract_candidate_path(user_input)
        run_now = self._wants_tool_execution(user_input) or self._is_direct_indexing_command(user_input)
        tool_calls = []
        
        if not indexer:
            return {
                'response': 'Document indexer not available. Check backend/sdoh_patient_index.py is present.',
                'score_adjustment': 0, 'is_ready': False, 'phase': 'error',
                'route': 'index_records',
            }
        
        if candidate_path:
            expanded = os.path.expanduser(candidate_path)
            path_exists = _win_isdir(expanded)
            
            if path_exists:
                # First, query the vault index for existing records
                vault_status = self._query_vault_index_for_folder(expanded)
                vault_count = vault_status.get('count', 0)
                vault_modalities = vault_status.get('modalities', {})
                
                # Quick sample for immediate feedback on large archives
                sample_result = indexer.quick_sample_files(
                    expanded,
                    max_files=20,
                    timeout_sec=60,
                )
                sample_files = sample_result.get('files', [])
                sample_count = sample_result.get('count', 0)
                sample_elapsed = sample_result.get('elapsed_sec', 0)
                sample_error = sample_result.get('error', None)
                
                # Add sampled files to index immediately
                existing_paths = {e.get('file_path', '') for e in indexer._index}
                for f in sample_files:
                    fp = f.get('FullName', '')
                    ext = (f.get('Extension') or os.path.splitext(fp)[1]).lower()
                    if fp and fp not in existing_paths and ext in indexer.SUPPORTED_EXTENSIONS:
                        try:
                            if ext == '.dcm':
                                entry = indexer._parse_dicom(fp)
                            elif ext in {'.jp2', '.j2k'}:
                                entry = indexer._parse_jp2(fp)
                            elif ext == '.pdf':
                                entry = indexer._parse_pdf(fp)
                            else:
                                entry = {'file_path': fp, 'file_type': ext.lstrip('.')}
                            if entry:
                                indexer._index.append(entry)
                        except Exception:
                            pass
                indexer._save_index()
                
                # Build appropriate message based on results
                vault_info = ""
                if vault_count > 0:
                    mod_summary = ", ".join(f"{k} ({v})" for k, v in sorted(vault_modalities.items()))
                    vault_info = f"\n\n📊 Vault index: {vault_count} records already indexed from this folder"
                    if mod_summary:
                        vault_info += f" — Modalities: {mod_summary}"
                
                if sample_error:
                    msg = (
                        f'✅ Scanned: {expanded}\n'
                        f'⚠️ Scan error: {sample_error}\n\n'
                        f'Total indexed: {len(indexer._index)}.{vault_info}\n\n'
                        f'Type "what documents do I have" to view your indexed files.'
                    )
                elif sample_count > 0:
                    msg = (
                        f'✅ Scanned: {expanded}\n'
                        f'Sampled {sample_count} file(s) in {sample_elapsed:.1f}s. '
                        f'Total indexed: {len(indexer._index)}.{vault_info}\n\n'
                        f'Found medical files in the archive. '
                        f'Type "what documents do I have" to view your indexed files.\n'
                        f'Type "prepare history pack" to build a sharing pack for your doctor.'
                    )
                else:
                    msg = (
                        f'✅ Scanned: {expanded}\n'
                        f'No files with recognised extensions found in sample scan. '
                        f'Total indexed: {len(indexer._index)}.{vault_info}\n\n'
                        f'If this is a DICOM archive, the files may be stored without a .dcm extension. '
                        f'Type "what documents do I have" to view your indexed files.'
                    )
                
                tool_calls.append({
                    'name': 'sdoh.index_documents',
                    'status': 'executed',
                    'args': {'folder': expanded},
                })
            else:
                msg = (
                    f'⚠️ Path not found: {expanded}\n\n'
                    'The folder could not be accessed. If this is a mapped network drive (e.g. X:\\), '
                    'please ensure the drive is accessible from the same session that runs the SDOH agent. '
                    'You can also try using the UNC path instead (e.g. \\\\server\\share\\UV images\\2018).'
                )
                tool_calls.append({
                    'name': 'sdoh.index_documents',
                    'status': 'error',
                    'args': {'folder': expanded, 'error': 'path_not_found'},
                })
            
            return {
                'response': msg,
                'score_adjustment': 0, 'is_ready': False, 'phase': 'index_records',
                'route': 'index_records',
                'new_insight': 'Indexing local medical files gives patients real control of their health data.',
                'insight_type': 'strength', 'confidence': 'high', 'verification_required': False,
                'timeline_items': [], 'draft_message': None, 'barrier_type': None,
                'barrier_classification': None, 'severity': 'low', 'continuity_priority': 'low',
                'clinician_summary': None, 'missed_window_reclamation': False,
                'source_paragraph': None, 'extracted_task': None, 'anatomy': None,
                'modality': None, 'timeline': None, 'export_bundle': None,
                'patient_validation_required': False, 'patient_validation_verified': False,
                'outbound_ready': False, 'patient_device_only': True,
                'tool_calls': tool_calls,
            }
        
        # No candidate path — scan default folders
        result = indexer.scan_all_default_dirs()
        msg = (
            f"I scanned your default medical records folders and found {result.get('total_scanned', 0)} file(s).\n"
            f"{result.get('total_new', 0)} new document(s) were added. Total indexed: {result.get('total_indexed', 0)}.\n\n"
            "Type 'what documents do I have' to view your indexed files."
        )
        return {
            'response': msg,
            'score_adjustment': 0, 'is_ready': False, 'phase': 'index_records',
            'route': 'index_records',
            'tool_calls': [{'name': 'sdoh.index_documents', 'status': 'executed', 'args': {'folder': '<default-folders>'}}],
        }

    def _build_siim_ingest_response(self, user_input: str, user_alias: str = 'Patient') -> Dict[str, Any]:
        """Start or check SIIM hackathon ingestion job and return progress response."""
        text_lower = (user_input or '').lower()
        try:
            from backend.siim_hackathon import start_ingest_job, get_ingest_state
            
            # If user is just asking for status, return current state without starting
            if 'status' in text_lower and 'start' not in text_lower and 'full' not in text_lower:
                state = get_ingest_state()
                status = state.get('status', 'idle')
                if status == 'running':
                    progress = state.get('progress', {})
                    done = sum(1 for v in progress.values() if v.get('fetched', 0) > 0)
                    total = len(progress) or 1
                    msg = f'⏳ SIIM ingest is running ({done}/{total} resource types processed). Check back in a moment.'
                elif status == 'completed':
                    report = state.get('report', {})
                    dicom = state.get('dicom', {})
                    msg = (
                        f'✅ SIIM ingest completed at {state.get("finished_at", "unknown")}.\n'
                        f'DICOM: {dicom.get("instances_downloaded", 0)} instances downloaded, '
                        f'{dicom.get("studies_found", 0)} studies found.\n'
                        f'Type "show me my SIIM patients" to view the indexed records.'
                    )
                elif status == 'error':
                    errors = state.get('errors', [])
                    msg = f'❌ SIIM ingest encountered an error: {errors[-1] if errors else "unknown"}.\nType "Start full SIIM ingest" to retry.'
                else:
                    msg = 'ℹ️ SIIM ingest has not been started yet. Type "Start full SIIM ingest" to begin.'
                return {
                    'response': msg,
                    'score_adjustment': 0, 'is_ready': False, 'phase': 'siim_ingest',
                    'route': 'siim_ingest',
                }
            
            # Start the ingest job
            result = start_ingest_job()
            if result.get("status") == "already_running":
                state = result.get("state", {})
                progress = state.get('progress', {})
                done = sum(1 for v in progress.values() if v.get('fetched', 0) > 0)
                total = len(progress) or 1
                return {
                    'response': (
                        f'⏳ SIIM ingest is already running in the background '
                        f'({done}/{total} resource types processed so far). '
                        f'Type "SIIM ingest status" to check progress.'
                    ),
                    'score_adjustment': 0, 'is_ready': False, 'phase': 'siim_ingest',
                    'route': 'siim_ingest'
                }
            
            return {
                'response': (
                    '🚀 SIIM Hackathon ingest started in the background!\n\n'
                    'Fetching FHIR patients, conditions, observations, imaging studies and DICOM metadata '
                    'from hackathon.siim.org...\n\n'
                    'Type "SIIM ingest status" at any time to check progress.'
                ),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'siim_ingest',
                'route': 'siim_ingest',
                'tool_calls': [{'name': 'sdoh.siim_ingest', 'status': 'started'}]
            }
        except Exception as exc:
            return {
                'response': f'❌ Failed to start SIIM ingest: {exc}',
                'score_adjustment': 0, 'is_ready': False, 'phase': 'error',
                'route': 'siim_ingest'
            }

    def _build_show_documents_response(self, user_input: str, user_alias: str = 'Patient') -> Dict[str, Any]:
        """Show indexed patients or documents from the health graph database with intelligent intent detection."""
        indexer = self._get_indexer()
        if not indexer:
            return {
                'response': 'Document indexer not available.',
                'score_adjustment': 0, 'is_ready': False, 'phase': 'error',
                'route': 'show_documents'
            }
        
        # Check if this is a query about a specific patient (e.g., "what is wrong with SIIM Neela")
        user_input_lower = user_input.lower()
        is_patient_specific = any(phrase in user_input_lower for phrase in [
            'what is wrong', 'what has been done', 'tell me more', 'what studies',
            'what procedures', 'what scans', 'any findings', 'any results',
            'what tests', 'any diagnosis'
        ])
        
        # Try to extract patient name if this is a patient-specific query
        patient_name = None
        if is_patient_specific:
            # Look for known SIIM patient names or generic patterns
            import re
            siim_names = ['neela', 'ravi', 'andy', 'sally', 'john', 'jane', 'mary', 'robert']
            for name in siim_names:
                if name in user_input_lower:
                    patient_name = name
                    break
            
            # If we found a patient name, query for their details
            if patient_name:
                try:
                    from backend.pacs_registry import PACSContinuityRegistry
                    registry = PACSContinuityRegistry()
                    patients = registry.list_patients(limit=100)
                    
                    # Find matching patient
                    matching_patients = []
                    for p in patients:
                        name = (p.get('patient_name') or 'Unknown').lower()
                        if patient_name in name:
                            matching_patients.append(p)
                    
                    if matching_patients:
                        patient = matching_patients[0]
                        name = patient.get('patient_name', 'Unknown')
                        empi_id = patient.get('empi_id', 'Unknown')
                        study_count = patient.get('study_count', 0)
                        
                        # Format patient name properly
                        if isinstance(name, dict) and 'Alphabetic' in name:
                            import ast
                            try:
                                name = ast.literal_eval(str(name)).get('Alphabetic', str(name))
                                name = name.replace('^', ' ').strip()
                            except Exception:
                                pass
                        
                        lines = [f'📋 Patient: {name}']
                        lines.append(f'   EMPI ID: {empi_id}')
                        lines.append(f'   Total Studies in Registry: {study_count}\n')
                        
                        # Get detailed studies from health graph database if available
                        if hasattr(indexer, 'db') and indexer.db:
                            try:
                                # Search for all studies for this patient
                                from backend.health_graph_schema import HealthGraphSchema
                                db = indexer.db
                                
                                # Get patient ID from database
                                patient_records = db.search_patients(patient_name, limit=10)
                                
                                if patient_records:
                                    lines.append(f'📚 Studies and Procedures from Health Graph Database:')
                                    
                                    for patient_record in patient_records[:3]:
                                        patient_id = patient_record.get('patient_id')
                                        if patient_id:
                                            # Get all studies for this patient
                                            all_studies = db.get_patient_studies(patient_id)
                                            
                                            if all_studies:
                                                for study_idx, study in enumerate(all_studies[:5], 1):
                                                    study_date = study.get('study_date', 'Unknown')
                                                    modality = study.get('modality', 'Unknown')
                                                    body_part = study.get('body_part_normalized', 'Unknown')
                                                    description = study.get('study_description', 'No description')
                                                    series_count = study.get('series_count', 0)
                                                    
                                                    lines.append(f'\n  Study {study_idx}:')
                                                    lines.append(f'    📅 Date: {study_date}')
                                                    lines.append(f'    🔬 Modality: {modality}')
                                                    lines.append(f'    🏥 Body Part: {body_part}')
                                                    lines.append(f'    📝 Description: {description}')
                                                    lines.append(f'    🖼️  Series: {series_count}')
                            except Exception as e:
                                print(f"[MIXIN] Database query error: {e}")
                                lines.append(f'\n  ⚠️  Could not retrieve detailed study information: {e}')
                        
                        if study_count == 0:
                            lines.append(f'\n⚠️  No studies found in registry for this patient.')
                        
                        lines.append(f'\n---')
                        lines.append(f'Type "Show me SIIM patients" to see all patients, or ask about another patient.')
                        
                        return {
                            'response': '\n'.join(lines),
                            'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                            'route': 'show_documents',
                        }
                except Exception as e:
                    print(f"[MIXIN] Patient lookup error: {e}")
        
        # Query health graph database with user's question for intelligent intent handling
        hg_data = indexer.query_health_graph_db(user_input)
        
        # If asking for a specific SIIM patient, show that patient's details
        if hg_data.get('filter_type') == 'siim_patient':
            patients = hg_data.get('filtered_patients', [])
            if patients:
                # Show details for the specific SIIM patient(s)
                lines = []
                if len(patients) == 1:
                    p = patients[0]
                    patient_id = p.get('patient_id')
                    lines.append(f"📋 Patient: {p.get('patient_name')}")
                    lines.append(f"   ID: {patient_id or '...'}")
                    if p.get('dob'):
                        lines.append(f"   DOB: {p.get('dob')}")
                    lines.append(f"   Total Studies: {p.get('total_studies', 0)}\n")
                    
                    if hasattr(indexer, 'db') and indexer.db and patient_id:
                        try:
                            all_studies = indexer.db.get_patient_studies(patient_id)
                            if all_studies:
                                lines.append(f'📚 Studies and Procedures:')
                                for study_idx, study in enumerate(all_studies[:10], 1):
                                    study_date = study.get('study_date', 'Unknown')
                                    modality = study.get('modality', 'Unknown')
                                    body_part = study.get('body_part_normalized', 'Unknown')
                                    description = study.get('study_description', 'No description')
                                    lines.append(f'\n  Study {study_idx}:')
                                    lines.append(f'    📅 Date: {study_date}')
                                    lines.append(f'    🔬 Modality: {modality}')
                                    lines.append(f'    🏥 Body Part: {body_part}')
                                    lines.append(f'    📝 Description: {description}')
                                if len(all_studies) > 10:
                                    lines.append(f'\n  ... and {len(all_studies) - 10} more studies')
                            else:
                                lines.append(f'\n⚠️  No studies found in database for this patient.')
                        except Exception as e:
                            print(f"[MIXIN] Database query error: {e}")
                            lines.append(f'\n  ⚠️  Could not retrieve detailed study information: {e}')
                    
                    lines.append("")
                    lines.append("Type \"SIIM ingest status\" to check ingest progress.")
                else:
                    lines.append(f"📋 Found {len(patients)} SIIM patient(s) matching your search:\n")
                    for p in patients[:10]:
                        name = p.get('patient_name') or 'Unknown'
                        patient_id = p.get('patient_id') or 'N/A'
                        studies = p.get('total_studies', 0)
                        dob = p.get('dob') or 'N/A'
                        lines.append(f"• {name} (ID: {patient_id[:15]}…, DOB: {dob}) — {studies} study/studies")
                    if len(patients) > 10:
                        lines.append(f'  … and {len(patients) - 10} more.')
                    lines.append('\nType "SIIM ingest status" to check ingest progress.')
                
                return {
                    'response': '\n'.join(lines),
                    'score_adjustment': 0.5, 'is_ready': True, 'phase': 'complete',
                    'route': 'query_response'
                }
            return {
                'response': 'No SIIM patients found matching that name.',
                'score_adjustment': 0, 'is_ready': False, 'phase': 'complete'
            }
        
        # If asking for all SIIM patients (generic SIIM ingest list)
        if hg_data.get('filter_type') == 'siim_ingest':
            # Query SIIM registry and show SIIM patients instead
            try:
                from backend.pacs_registry import PACSContinuityRegistry
                registry = PACSContinuityRegistry()
                patients = registry.list_patients(limit=20)
                if patients:
                    lines = [f'📋 Found {len(patients)} patient(s) in your SIIM registry:\n']
                    for p in patients[:10]:
                        name = p.get('patient_name') or 'Unknown'
                        if isinstance(name, str) and 'Alphabetic' in name:
                            import ast
                            try:
                                parsed_name = ast.literal_eval(name).get('Alphabetic', name)
                                name = parsed_name.replace('^', ' ').strip()
                            except Exception:
                                pass
                        pid = p.get('empi_id', '')[:8]
                        studies = p.get('study_count', 0)
                        lines.append(f'  • {name} (ID: {pid}…) — {studies} study/studies')
                    if len(patients) > 10:
                        lines.append(f'  … and {len(patients) - 10} more.')
                    lines.append('\nType "SIIM ingest status" to check ingest progress, or "prepare history pack" to export records.')
                    return {
                        'response': '\n'.join(lines),
                        'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                        'route': 'show_documents',
                    }
            except Exception as e:
                print(f"[MIXIN] SIIM registry error: {e}")
            
            # If SIIM registry lookup fails, return empty so proxy can handle it
            return {'success': False}
        
        # Handle patient name search with no results
        if hg_data.get('filter_type') == 'patient_name' and not hg_data.get('success'):
            search_firstname = hg_data.get('search_firstname', '')
            search_lastname = hg_data.get('search_lastname', '')
            
            if search_firstname and search_lastname:
                name_str = f"{search_firstname} {search_lastname}"
            else:
                name_str = search_firstname or search_lastname or "unknown"
            
            return {
                'response': f'No patients found with the name "{name_str}".',
                'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                'route': 'show_documents',
            }
        
        if hg_data.get('success'):
            # Handle summary/overview queries
            if hg_data.get('filter_type') == 'summary':
                total_patients = hg_data.get('total_patients', 0)
                total_studies = hg_data.get('total_studies', 0)
                total_files = hg_data.get('total_files', 0)
                
                lines = [
                    f'📋 Health Graph Database Summary:\n',
                    f'   Total Patients: {total_patients:,}',
                    f'   Total Studies: {total_studies:,}',
                    f'   Total Files Indexed: {total_files:,}\n',
                ]
                
                patients = hg_data.get('patients', [])
                if patients:
                    lines.append(f'Recent patients:')
                    for p in patients[:10]:
                        name = p.get('patient_name', 'Unknown')
                        pid = p.get('patient_id', '')[:8]
                        studies = p.get('total_studies', 0)
                        lines.append(f'  • {name} (ID: {pid}…) — {studies} study/studies')
                    
                    if len(patients) > 10:
                        lines.append(f'  … and {len(patients) - 10} more.')
                
                lines.append('\nYou can ask me about specific patients or imaging studies.')
                
                return {
                    'response': '\n'.join(lines),
                    'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                    'route': 'show_documents',
                }
            
            # Handle birth year filter
            if hg_data.get('filter_type') == 'birth_year_filter':
                filter_year = hg_data.get('filter_birth_year', '')
                filtered = hg_data.get('filtered_patients', [])
                
                if filtered:
                    lines = [f'📋 Patients born in {filter_year}:\n']
                    for p in filtered[:10]:
                        name = p.get('patient_name', 'Unknown')
                        dob = p.get('dob', 'Unknown')
                        studies = p.get('total_studies', 0)
                        pid = p.get('patient_id', '')[:8]
                        lines.append(f'  • {name} (DOB: {dob}, ID: {pid}…) — {studies} study/studies')
                    
                    if len(filtered) > 10:
                        lines.append(f'  … and {len(filtered) - 10} more.')
                    
                    lines.append(f'\nTotal patients born in {filter_year}: {hg_data.get("total_found", 0)}')
                    
                    return {
                        'response': '\n'.join(lines),
                        'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                        'route': 'show_documents',
                    }
                else:
                    return {
                        'response': f'No patients found born in {filter_year}.',
                        'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                        'route': 'show_documents',
                    }
            
            # Handle year-based filter (e.g., "how many patients in 2015")
            if hg_data.get('filter_type') == 'year_filter':
                filter_year = hg_data.get('filter_year', '')
                filtered = hg_data.get('filtered_patients', [])
                total_studies = hg_data.get('total_studies_found', 0)
                
                if filtered:
                    lines = [f'📋 Patients with studies in {filter_year}:\n']
                    for p in filtered[:10]:
                        name = p.get('patient_name', 'Unknown')
                        studies_count = p.get('total_studies', 0)
                        pid = p.get('patient_id', '')[:8]
                        lines.append(f'  • {name} (ID: {pid}…) — {studies_count} study/studies')
                    
                    if len(filtered) > 10:
                        lines.append(f'  … and {len(filtered) - 10} more.')
                    
                    lines.append(f'\nTotal studies in {filter_year}: {total_studies}')
                    
                    return {
                        'response': '\n'.join(lines),
                        'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                        'route': 'show_documents',
                    }
                else:
                    return {
                        'response': f'No patients found with studies in {filter_year}.',
                        'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                        'route': 'show_documents',
                    }
            
            # Handle filtered patient search (by name)
            if hg_data.get('filter_type') == 'patient_name':
                filtered = hg_data.get('filtered_patients', [])
                search_lastname = hg_data.get('search_lastname', '')
                search_firstname = hg_data.get('search_firstname', '')
                search_name = hg_data.get('search_name', search_lastname or search_firstname or '')
                
                # Build a descriptive search name for the response
                if search_firstname and search_lastname:
                    display_name = f"{search_firstname} {search_lastname}"
                else:
                    display_name = search_name
                
                if filtered:
                    lines = []
                    
                    # If only one patient found, show detailed studies
                    if len(filtered) == 1:
                        patient = filtered[0]
                        patient_id = patient.get('patient_id')
                        patient_name = patient.get('patient_name', display_name)
                        dob = patient.get('dob', 'Unknown')
                        total_studies = patient.get('total_studies', 0)
                        
                        lines.append(f'📋 Patient: {patient_name}')
                        lines.append(f'   ID: {patient_id[:8]}...')
                        lines.append(f'   DOB: {dob}')
                        lines.append(f'   Total Studies: {total_studies}\n')
                        
                        # Get detailed studies from database if available
                        if hasattr(indexer, 'db') and indexer.db and patient_id:
                            try:
                                all_studies = indexer.db.get_patient_studies(patient_id)
                                
                                if all_studies:
                                    lines.append(f'📚 Studies and Procedures:')
                                    for study_idx, study in enumerate(all_studies[:10], 1):
                                        study_date = study.get('study_date', 'Unknown')
                                        modality = study.get('modality', 'Unknown')
                                        body_part = study.get('body_part_normalized', 'Unknown')
                                        description = study.get('study_description', 'No description')
                                        
                                        lines.append(f'\n  Study {study_idx}:')
                                        lines.append(f'    📅 Date: {study_date}')
                                        lines.append(f'    🔬 Modality: {modality}')
                                        lines.append(f'    🏥 Body Part: {body_part}')
                                        lines.append(f'    📝 Description: {description}')
                                    
                                    if len(all_studies) > 10:
                                        lines.append(f'\n  ... and {len(all_studies) - 10} more studies')
                                else:
                                    lines.append(f'\n⚠️  No studies found in database for this patient.')
                            except Exception as e:
                                print(f"[MIXIN] Database query error: {e}")
                                lines.append(f'\n  ⚠️  Could not retrieve detailed study information: {e}')
                        
                    else:
                        # Multiple patients found - show list
                        if search_firstname and search_lastname:
                            lines.append(f'📋 Found {hg_data.get("total_found", 0)} patient(s) named "{display_name}":\n')
                        else:
                            lines.append(f'📋 Found {hg_data.get("total_found", 0)} patient(s) with surname "{display_name}":\n')
                        
                        for p in filtered[:10]:
                            name = p.get('patient_name', 'Unknown')
                            pid = p.get('patient_id', '')[:8]
                            studies = p.get('total_studies', 0)
                            dob = p.get('dob', 'Unknown')
                            lines.append(f'  • {name} (ID: {pid}…, DOB: {dob}) — {studies} study/studies')
                        
                        if hg_data.get('total_found', 0) > 10:
                            lines.append(f'  … and {hg_data.get("total_found", 0) - 10} more.')
                    
                    return {
                        'response': '\n'.join(lines),
                        'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                        'route': 'show_documents',
                    }
                else:
                    return {
                        'response': f'No patients found with name "{display_name}".',
                        'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                        'route': 'show_documents',
                    }
            
            # Handle modality/body part filtered search
            if hg_data.get('filter_type') == 'modality_or_bodypart':
                filtered = hg_data.get('filtered_patients', [])
                mod = hg_data.get('filter_modality', '')
                bp = hg_data.get('filter_body_part', '')
                
                filter_desc = f'{mod} {bp} studies'.strip()
                total = hg_data.get('total_studies_found', 0)
                
                lines = [f'📋 Found {total} {filter_desc}:\n']
                for p in filtered[:10]:
                    name = p.get('patient_name', 'Unknown')
                    pid = p.get('patient_id', '')[:8]
                    studies_count = p.get('total_studies', 0)
                    lines.append(f'  • {name} (ID: {pid}…) — {studies_count} studies')
                
                if len(filtered) > 10:
                    lines.append(f'  … and {len(filtered) - 10} more.')
                
                return {
                    'response': '\n'.join(lines),
                    'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                    'route': 'show_documents',
                }
        
        # Fallback to SIIM registry for SIIM-related queries
        try:
            from backend.pacs_registry import PACSContinuityRegistry
            registry = PACSContinuityRegistry()
            patients = registry.list_patients(limit=20)
            if patients:
                lines = [f'📋 Found {len(patients)} patient(s) in your SIIM registry:\n']
                for p in patients[:10]:
                    name = p.get('patient_name') or 'Unknown'
                    if isinstance(name, str) and 'Alphabetic' in name:
                        import ast
                        try:
                            parsed_name = ast.literal_eval(name).get('Alphabetic', name)
                            name = parsed_name.replace('^', ' ').strip()
                        except Exception:
                            pass
                    pid = p.get('empi_id', '')[:8]
                    studies = p.get('study_count', 0)
                    lines.append(f'  • {name} (ID: {pid}…) — {studies} study/studies')
                if len(patients) > 10:
                    lines.append(f'  … and {len(patients) - 10} more.')
                lines.append('\nType "SIIM ingest status" to check ingest progress, or "prepare history pack" to export records.')
                return {
                    'response': '\n'.join(lines),
                    'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                    'route': 'show_documents',
                }
        except Exception:
            pass
        
        # No data found
        msg = (
            "I haven't indexed any documents yet.\n\n"
            "You can:\n"
            "• Type \"Start full SIIM ingest\" to fetch patient data from hackathon.siim.org\n"
            "• Type \"scan this folder (X:\\path\\to\\dicom)\" to index local DICOM files"
        )
            
        return {
            'response': msg,
            'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
            'route': 'show_documents',
        }

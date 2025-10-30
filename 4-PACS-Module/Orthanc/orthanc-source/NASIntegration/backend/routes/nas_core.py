"""NAS API registrar and small utilities.

This module intentionally stays small but practical. It preserves the
module-level variable ``nas_core_bp`` for backward compatibility while
making imports of the sub-blueprints tolerant to import errors and
providing a small helper to register the blueprint on an application.

Extras:
- safe import of `discovery` and `devices` sub-blueprints (log on error)
- `register_nas_blueprints(app, url_prefix)` convenience helper
- a lightweight debug endpoint ``/_routes`` which lists registered
  endpoints for this blueprint (only exposed when `app.debug` or
  when `NAS_CORE_EXPOSE_ROUTES` is True).
"""

import logging
import os
import json
import urllib.parse
from pathlib import Path
from flask import Blueprint, current_app, jsonify, request, send_file, redirect, render_template
from typing import Optional
from flask import Response
import requests
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Primary blueprint object kept for backward compatibility with imports
nas_core_bp = Blueprint('nas_core', __name__)

# Simple in-memory download job tracker for background ZIP creation
DOWNLOAD_JOBS = {}

def _make_download_job(patient_id, format_type, study_uid=None):
	import uuid
	job_id = str(uuid.uuid4())
	DOWNLOAD_JOBS[job_id] = {
		'patient_id': patient_id,
		'study_uid': study_uid,
		'format': format_type,
		'state': 'queued',
		'progress': 0,
		'file_path': None,
		'filename': None,
		'error': None,
		'started_at': None,
		'finished_at': None
	}
	return job_id

def _run_download_job(job_id):
	import threading, time, importlib.util, sys, tempfile, zipfile
	job = DOWNLOAD_JOBS.get(job_id)
	if not job:
		return
	job['state'] = 'running'
	job['progress'] = 5
	job['started_at'] = datetime.now().isoformat()
	try:
		# Locate medical-reporting-module and load its dicom_download_service module
		this_dir = os.path.abspath(os.path.dirname(__file__))
		medical_module_path = None
		search_dir = this_dir
		for _ in range(6):
			candidate = os.path.join(search_dir, 'medical-reporting-module')
			if os.path.isdir(candidate):
				medical_module_path = candidate
				break
			parent = os.path.dirname(search_dir)
			if parent == search_dir:
				break
			search_dir = parent

		if not medical_module_path:
			candidate = os.path.abspath(os.path.join(this_dir, '..', '..', 'medical-reporting-module'))
			if os.path.isdir(candidate):
				medical_module_path = candidate

		if not medical_module_path:
			job['state'] = 'error'
			job['error'] = 'Download service unavailable'
			job['progress'] = 0
			return

		service_file = os.path.join(medical_module_path, 'services', 'dicom_download_service.py')
		if not os.path.exists(service_file):
			job['state'] = 'error'
			job['error'] = 'Download service file not found'
			job['progress'] = 0
			return

		spec = importlib.util.spec_from_file_location('mr_dicom_download_service', service_file)
		mod = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(mod)

		DICOMDownloadService = getattr(mod, 'DICOMDownloadService', None)
		if not DICOMDownloadService:
			job['state'] = 'error'
			job['error'] = 'Download service class not found'
			job['progress'] = 0
			return

		service = DICOMDownloadService()
		studies = service.get_patient_studies(job['patient_id'], job.get('study_uid'))
		if not studies:
			job['state'] = 'error'
			job['error'] = f"No studies found for patient {job['patient_id']}"
			job['progress'] = 0
			return

		# Give a small heartbeat after studies discovered so UI shows activity
		job['progress'] = max(job.get('progress', 5), 10)
		job['message'] = f"Discovered {len(studies)} study(ies); scanning files..."

		# First pass: count total files to give progress estimate
		total_files = 0
		file_lists = []
		for idx, s in enumerate(studies, start=1):
			# Respect cancellation
			if job.get('state') == 'cancelled':
				job['error'] = 'Cancelled by user'
				job['progress'] = 0
				job['finished_at'] = datetime.now().isoformat()
				job['state'] = 'cancelled'
				return
			# Try to find files for this study; protect against long hangs
			try:
				files = service.find_dicom_files(s)
			except Exception as e:
				logger.warning(f"find_dicom_files failed for study {s.get('study_uid') or s.get('study_id')}: {e}")
				files = []
			file_lists.append((s, files))
			total_files += len(files)
			# Update progress so UI shows per-study scanning progress (10-40%)
			try:
				scan_progress = 10 + int((idx / max(1, len(studies))) * 30)
				job['progress'] = max(job.get('progress', 5), scan_progress)
			except Exception:
				pass

		# If no files found
		if total_files == 0:
			job['state'] = 'error'
			job['error'] = 'No DICOM files found for selected studies'
			job['progress'] = 0
			return

		# Create ZIP incrementally and update progress
		tmp_dir = tempfile.mkdtemp(prefix=f"dicom_job_{job_id}_")
		zip_filename = f"DICOM_{job['patient_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
		zip_path = os.path.join(tmp_dir, zip_filename)
		added = 0
		# Move progress into a visible range before long ZIP write to avoid UI appearing stuck
		job['progress'] = max(job.get('progress', 5), 40)
		job['message'] = f"Creating ZIP archive ({total_files} files)..."
		
		# Use ZIP_STORED (no compression) for LAN speed - DICOM files are already compressed
		# This is 10-20x faster than ZIP_DEFLATED for large medical images over LAN
		with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zf:
			for s, files in file_lists:
				if job.get('state') == 'cancelled':
					job['error'] = 'Cancelled by user'
					job['progress'] = 0
					job['state'] = 'cancelled'
					job['finished_at'] = datetime.now().isoformat()
					return
				study_uid = s.get('study_uid') or s.get('study_id') or ''
				study_date = s.get('study_date') or ''
				study_desc = s.get('description') or 'study'
				study_folder = f"{study_date}_{study_desc}_{str(study_uid)[:8]}"
				study_folder = "".join(c for c in study_folder if c.isalnum() or c in '._-')
				for fpath in files:
					try:
						arcname = os.path.join(study_folder, os.path.basename(fpath)).replace('\\','/')
						zf.write(fpath, arcname)
						added += 1
						# Update progress more frequently (every file) for smoother UI updates
						if total_files:
							scaled = 40 + int((added / total_files) * 55)
							job['progress'] = max(job.get('progress', 40), min(95, scaled))
							# Update message every 50 files to show activity without spamming
							if added % 50 == 0 or added == total_files:
								job['message'] = f"Adding files: {added}/{total_files}"
					except Exception as e:
						logger.debug(f"Failed to add file to zip: {fpath}, error: {e}")
						continue

		# Finalize job
		job['file_path'] = zip_path
		job['filename'] = zip_filename
		job['progress'] = 100
		job['state'] = 'ready'

	except Exception as e:
		job['state'] = 'error'
		job['error'] = str(e)
		job['progress'] = 0
	finally:
		job['finished_at'] = datetime.now().isoformat()


@nas_core_bp.route('/download/job', methods=['POST'])
def create_download_job():
	data = request.get_json() or {}
	patient_id = data.get('patient_id')
	study_uid = data.get('study_uid')
	format_type = data.get('format', 'zip')
	if not patient_id:
		return jsonify({'success': False, 'error': 'patient_id required'}), 400

	# Only background ZIP jobs for now
	job_id = _make_download_job(patient_id, format_type, study_uid)

	# Start worker thread
	import threading
	t = threading.Thread(target=_run_download_job, args=(job_id,), daemon=True)
	t.start()

	return jsonify({'success': True, 'job_id': job_id})


@nas_core_bp.route('/download/job/<job_id>/status', methods=['GET'])
def download_job_status(job_id):
	job = DOWNLOAD_JOBS.get(job_id)
	if not job:
		return jsonify({'success': False, 'error': 'job not found'}), 404
	# Do not expose file_path except when ready
	safe = {k: v for k, v in job.items() if k not in ('file_path',)}
	if job.get('state') == 'ready':
		safe['download_url'] = f"/api/nas/download/job/{job_id}/file"
	return jsonify({'success': True, 'job': safe})


@nas_core_bp.route('/download/job/<job_id>/file', methods=['GET'])
def download_job_file(job_id):
	job = DOWNLOAD_JOBS.get(job_id)
	if not job:
		return jsonify({'success': False, 'error': 'job not found'}), 404
	if job.get('state') != 'ready' or not job.get('file_path'):
		return jsonify({'success': False, 'error': 'file not ready'}), 404
	try:
		return send_file(job['file_path'], as_attachment=True, download_name=job.get('filename'))
	except Exception as e:
		return jsonify({'success': False, 'error': str(e)}), 500


@nas_core_bp.route('/download/jobs', methods=['GET'])
def list_download_jobs():
	# Return summary of all jobs
	jobs = {jid: {k: v for k, v in j.items() if k not in ('file_path',)} for jid, j in DOWNLOAD_JOBS.items()}
	return jsonify({'success': True, 'jobs': jobs})


@nas_core_bp.route('/download/job/<job_id>/cancel', methods=['POST'])
def cancel_download_job(job_id):
	job = DOWNLOAD_JOBS.get(job_id)
	if not job:
		return jsonify({'success': False, 'error': 'job not found'}), 404
	# Mark as cancelled; worker should respect this if it checks state
	job['state'] = 'cancelled'
	job['error'] = 'Cancelled by user'
	job['progress'] = 0
	job['finished_at'] = datetime.now().isoformat()
	return jsonify({'success': True, 'job': {k: v for k, v in job.items() if k != 'file_path'}})


# Basic Orthanc configuration (can be overridden via environment)
ORTHANC_URL = os.environ.get('ORTHANC_URL', 'http://localhost:8042')
ORTHANC_USERNAME = os.environ.get('ORTHANC_USERNAME', 'orthanc')
ORTHANC_PASSWORD = os.environ.get('ORTHANC_PASSWORD', 'orthanc')

def _forward_orthanc(method: str, path: str, stream: bool = True):
	"""Forward a request to the local Orthanc server with basic auth."""
	url = f"{ORTHANC_URL.rstrip('/')}/{path.lstrip('/')}"
	headers = {k: v for k, v in request.headers.items() if k.lower() not in (
		'host', 'content-length', 'accept-encoding', 'connection')}
	data = request.get_data() if method in ('POST', 'PUT', 'PATCH') else None

	resp = requests.request(
		method=method,
		url=url,
		headers=headers,
		data=data,
		params=request.args,
		auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
		stream=stream,
		timeout=60,
	)

	excluded = set(['content-encoding', 'transfer-encoding', 'connection'])
	response_headers = [(name, value) for name, value in resp.raw.headers.items()
						if name.lower() not in excluded]

	return Response(resp.raw if stream else resp.content,
					status=resp.status_code,
					headers=response_headers)

@nas_core_bp.route('/orthanc-proxy/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def orthanc_proxy(path):
	"""Reverse proxy to Orthanc to avoid client-side localhost and CORS issues."""
	return _forward_orthanc(request.method, path)

@nas_core_bp.route('/dicom-web/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def dicomweb_proxy(path):
	"""Reverse proxy specifically for Orthanc DICOMweb endpoints."""
	return _forward_orthanc(request.method, f"dicom-web/{path}")


# -----------------------------
# Helpers for NAS <-> DICOM ops
# -----------------------------

def _get_patient_folder_from_db(patient_id: str) -> Optional[str]:
	"""Lookup a patient's NAS folder from the local NAS index DB.

	Returns a Windows/UNC or POSIX path if present, else None.
	"""
	try:
		# Prefer the canonical metadata DB path helper
		try:
			from ..metadata_db import get_metadata_db_path
		except Exception:
			from backend.metadata_db import get_metadata_db_path

		db_path = get_metadata_db_path()
		import sqlite3
		conn = sqlite3.connect(db_path, timeout=5)
		cur = conn.cursor()
		cur.execute("SELECT folder_path FROM patients WHERE patient_id = ?", (patient_id,))
		row = cur.fetchone()
		conn.close()
		if row and row[0]:
			folder = row[0]
			# Return the stored folder path (may be UNC or POSIX); caller will check existence
			return folder
		return None
	except Exception as e:
		logger.warning(f"Patient folder lookup failed: {e}")
		return None

# --- OneDrive OAuth helpers -------------------------------------------------
ONEDRIVE_CLIENT_ID = os.environ.get('ONEDRIVE_CLIENT_ID')
ONEDRIVE_CLIENT_SECRET = os.environ.get('ONEDRIVE_CLIENT_SECRET')
ONEDRIVE_REDIRECT = os.environ.get('ONEDRIVE_REDIRECT') or 'http://localhost:5000/api/nas/onedrive/callback'

def _token_store_path() -> Path:
	try:
		inst = current_app.instance_path
	except Exception:
		inst = os.path.join(os.getcwd(), 'instance')
	p = Path(inst) / 'onedrive_token.json'
	return p

def _save_onedrive_token(token_obj: dict):
	token_path = _token_store_path()
	try:
		os.makedirs(str(token_path.parent), exist_ok=True)
		with open(token_path, 'w', encoding='utf-8') as fh:
			json.dump(token_obj, fh)
		return True
	except Exception as e:
		logger.error(f"Failed to save OneDrive token: {e}")
		return False

def _load_onedrive_token() -> Optional[dict]:
	token_path = _token_store_path()
	try:
		if not token_path.exists():
			return None
		with open(token_path, 'r', encoding='utf-8') as fh:
			return json.load(fh)
	except Exception as e:
		logger.error(f"Failed to load OneDrive token: {e}")
		return None

def _clear_onedrive_token():
	token_path = _token_store_path()
	try:
		if token_path.exists():
			token_path.unlink()
		return True
	except Exception as e:
		logger.error(f"Failed to clear OneDrive token: {e}")
		return False

def _refresh_onedrive_token(refresh_token: str) -> Optional[dict]:
	"""Use refresh_token to obtain a new access token from Microsoft.

	Returns the token object from the token endpoint on success, else None.
	"""
	if not ONEDRIVE_CLIENT_ID or not ONEDRIVE_CLIENT_SECRET:
		logger.debug("Cannot refresh OneDrive token: client id/secret missing")
		return None
	token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
	data = {
		'client_id': ONEDRIVE_CLIENT_ID,
		'client_secret': ONEDRIVE_CLIENT_SECRET,
		'grant_type': 'refresh_token',
		'refresh_token': refresh_token,
	}
	try:
		resp = requests.post(token_url, data=data, timeout=15)
		if resp.status_code != 200:
			logger.warning(f"Refresh token request failed: {resp.status_code} {resp.text[:200]}")
			return None
		token_obj = resp.json()
		# populate expires_at if expires_in present
		try:
			if token_obj.get('expires_in'):
				token_obj['expires_at'] = (datetime.utcnow() + timedelta(seconds=int(token_obj.get('expires_in')))).isoformat()
		except Exception:
			pass
		return token_obj
	except Exception as e:
		logger.error(f"Error refreshing OneDrive token: {e}")
		return None


def _ensure_onedrive_token() -> Optional[str]:
	"""Return a usable OneDrive access token.

	Priority: ONEDRIVE_ACCESS_TOKEN env var -> saved token (refresh if expired) -> None
	"""
	# 1) environment override
	token = os.environ.get('ONEDRIVE_ACCESS_TOKEN') or os.environ.get('MICROSOFT_GRAPH_TOKEN')
	if token:
		return token

	# 2) saved token
	stored = _load_onedrive_token()
	if not stored:
		return None

	access = stored.get('access_token') or stored.get('accessToken')
	expires_at = stored.get('expires_at')
	refresh = stored.get('refresh_token') or stored.get('refreshToken')

	# If we have no expiry information, assume token is valid
	if not expires_at:
		return access

	try:
		exp = datetime.fromisoformat(expires_at)
	except Exception:
		# unknown format - return what we have
		return access

	# If token still valid for >30s, return it
	if exp > datetime.utcnow() + timedelta(seconds=30):
		return access

	# Token expired or close to expiry: try refresh
	if refresh:
		new_token_obj = _refresh_onedrive_token(refresh)
		if new_token_obj:
			# merge account info if present
			if 'account' in stored and 'account' not in new_token_obj:
				new_token_obj['account'] = stored.get('account')
			# compute expires_at
			try:
				if new_token_obj.get('expires_in'):
					new_token_obj['expires_at'] = (datetime.utcnow() + timedelta(seconds=int(new_token_obj.get('expires_in')))).isoformat()
			except Exception:
				pass
			_save_onedrive_token(new_token_obj)
			return new_token_obj.get('access_token') or new_token_obj.get('accessToken')

	# Could not refresh; return stale token (best-effort) or None
	return access

@nas_core_bp.route('/onedrive/login')
def onedrive_login():
	"""Redirect user to Microsoft OAuth to authorize OneDrive access."""
	if not ONEDRIVE_CLIENT_ID:
		return jsonify({'success': False, 'error': 'ONEDRIVE_CLIENT_ID not configured on server'}), 500
	params = {
		'client_id': ONEDRIVE_CLIENT_ID,
		'scope': 'offline_access Files.ReadWrite.All User.Read',
		'response_type': 'code',
		'redirect_uri': ONEDRIVE_REDIRECT,
	}
	auth_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize?' + urllib.parse.urlencode(params)
	return redirect(auth_url)


@nas_core_bp.route('/onedrive/setup')
def onedrive_setup_page():
	# Serve the setup UI
	return render_template('onedrive_setup.html')


# --- Backwards-compatible redirects for legacy unprefixed OneDrive URLs ---
@nas_core_bp.route('/_legacy/onedrive/<path:sub>', methods=['GET', 'POST'])
def _legacy_onedrive_redirect(sub):
	# Redirect internal legacy paths like /_legacy/onedrive/setup -> /api/nas/onedrive/setup
	target = f"/api/nas/onedrive/{sub}"
	return redirect(target)

@nas_core_bp.route('/onedrive', methods=['GET'])
def _onedrive_root_redirect():
	return redirect('/api/nas/onedrive/setup')


@nas_core_bp.route('/onedrive/callback')
def onedrive_callback():
	code = request.args.get('code')
	error = request.args.get('error')
	if error:
		return f"OAuth error: {error}", 400
	if not code:
		return 'Missing code in callback', 400
	# Exchange code for token
	token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
	data = {
		'client_id': ONEDRIVE_CLIENT_ID,
		'client_secret': ONEDRIVE_CLIENT_SECRET,
		'code': code,
		'grant_type': 'authorization_code',
		'redirect_uri': ONEDRIVE_REDIRECT,
	}
	try:
		resp = requests.post(token_url, data=data, timeout=30)
		if resp.status_code != 200:
			return f"Token exchange failed: {resp.status_code} {resp.text}", 500
		token_obj = resp.json()
		# Optionally fetch user email for display
		hdr = {'Authorization': f"Bearer {token_obj.get('access_token')}"}
		me = requests.get('https://graph.microsoft.com/v1.0/me', headers=hdr, timeout=10)
		if me.status_code == 200:
			token_obj['account'] = me.json()
		_save_onedrive_token(token_obj)
		return render_template('onedrive_setup.html', message='Connected successfully. You can close this page and return to Patients.')
	except Exception as e:
		logger.error(f"OneDrive callback error: {e}")
		return f"Error during token exchange: {e}", 500


@nas_core_bp.route('/onedrive/status', methods=['GET'])
def onedrive_status():
	t = _load_onedrive_token()
	if not t:
		return jsonify({'connected': False})
	account = t.get('account') or {}
	expires_at = t.get('expires_at') or None
	return jsonify({'connected': True, 'account_email': account.get('mail') or account.get('userPrincipalName'), 'expires_at': expires_at})


@nas_core_bp.route('/onedrive/config', methods=['GET'])
def onedrive_config():
	"""Return OneDrive OAuth configuration availability for the UI.

	Returns JSON: { configured: bool, client_id: str|null, redirect_uri: str }
	"""
	try:
		cfg = {
			'configured': bool(ONEDRIVE_CLIENT_ID),
			'client_id': ONEDRIVE_CLIENT_ID or None,
			'redirect_uri': ONEDRIVE_REDIRECT,
		}
		return jsonify(cfg)
	except Exception as e:
		logger.error(f"Error returning OneDrive config: {e}")
		return jsonify({'configured': False, 'client_id': None, 'redirect_uri': ONEDRIVE_REDIRECT}), 500


@nas_core_bp.route('/gdrive/config', methods=['GET'])
def gdrive_config():
	"""Return Google Drive OAuth configuration availability for the UI.

	Returns JSON: { configured: bool, client_id: str|null, redirect_uri: str }
	"""
	try:
		g_redirect = os.environ.get('GDRIVE_REDIRECT') or 'http://localhost:5000/api/nas/gdrive/callback'
		cfg = {
			'configured': bool(os.environ.get('GOOGLE_CLIENT_ID')),
			'client_id': os.environ.get('GOOGLE_CLIENT_ID') or None,
			'redirect_uri': g_redirect,
		}
		return jsonify(cfg)
	except Exception as e:
		logger.error(f"Error returning GDrive config: {e}")
		return jsonify({'configured': False, 'client_id': None, 'redirect_uri': 'http://localhost:5000/api/nas/gdrive/callback'}), 500


@nas_core_bp.route('/gdrive/setup')
def gdrive_setup_page():
	# Serve a simple GDrive setup UI
	return render_template('gdrive_setup.html')


@nas_core_bp.route('/gdrive/login')
def gdrive_login():
	"""Redirect user to Google's OAuth to authorize Drive access."""
	client_id = os.environ.get('GOOGLE_CLIENT_ID')
	client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
	redirect = os.environ.get('GDRIVE_REDIRECT') or 'http://localhost:5000/api/nas/gdrive/callback'
	if not client_id:
		return jsonify({'success': False, 'error': 'GOOGLE_CLIENT_ID not configured on server'}), 500
	# Build Google OAuth URL (basic flow)
	params = {
		'client_id': client_id,
		'response_type': 'code',
		'scope': 'https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/userinfo.email openid',
		'access_type': 'offline',
		'prompt': 'consent',
		'redirect_uri': redirect,
	}
	auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params)
	return redirect(auth_url)


@nas_core_bp.route('/onedrive/disconnect', methods=['POST'])
def onedrive_disconnect():
	_clear_onedrive_token()
	return jsonify({'success': True})


@nas_core_bp.route('/onedrive/manual_token', methods=['POST'])
def onedrive_manual_token():
	"""Accept a manually-provided OneDrive access token (developer/test fallback).

	Expected JSON: { access_token: str, refresh_token?: str, expires_in?: int, account_email?: str }
	This will be saved to the token store so the server can use the token for uploads.
	"""
	try:
		data = request.get_json() or {}
		access_token = data.get('access_token')
		if not access_token:
			return jsonify({'success': False, 'error': 'access_token required'}), 400
		token_obj = {'access_token': access_token}
		if 'refresh_token' in data and data.get('refresh_token'):
			token_obj['refresh_token'] = data.get('refresh_token')
		# compute an expiry timestamp if expires_in provided
		try:
			expires_in = int(data.get('expires_in')) if data.get('expires_in') is not None else None
		except Exception:
			expires_in = None
		if expires_in:
			token_obj['expires_at'] = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
		# optional account email
		if data.get('account_email'):
			token_obj['account'] = {'mail': data.get('account_email'), 'userPrincipalName': data.get('account_email')}

		saved = _save_onedrive_token(token_obj)
		if not saved:
			return jsonify({'success': False, 'error': 'failed to save token'}), 500
		return jsonify({'success': True})
	except Exception as e:
		logger.error(f"Manual OneDrive token save error: {e}")
		return jsonify({'success': False, 'error': str(e)}), 500


def _iter_dicom_files(patient_id: str, study_uid: Optional[str] = None, hard_limit: int = 500):
	"""Yield DICOM file paths for a patient, optionally filtered by StudyInstanceUID.

	Tries the dedicated service if available, else walks the patient's folder from DB.
	"""
	# 1) Try dedicated service if present
	try:
		import sys
		# Compute the Orthanc repo root (4 levels up from this file)
		orthanc_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
		medical_module_path = os.path.join(orthanc_root, 'medical-reporting-module')
		if medical_module_path not in sys.path:
			sys.path.insert(0, medical_module_path)
		from services import nas_dicom_search  # type: ignore
		files = nas_dicom_search.find_patient_dicom_files(patient_id, None)
		count = 0
		if study_uid:
			try:
				import pydicom
			except Exception:
				pydicom = None
			for f in files:
				path = f if isinstance(f, str) else f.get('file_path')
				if not path:
					continue
				if study_uid and pydicom is not None:
					try:
						ds = pydicom.dcmread(path, stop_before_pixels=True, specific_tags=['StudyInstanceUID'])
						if str(getattr(ds, 'StudyInstanceUID', '')) != str(study_uid):
							continue
					except Exception:
						pass
				yield path
				count += 1
				if count >= hard_limit:
					break
		else:
			for f in files[:hard_limit]:
				path = f if isinstance(f, str) else f.get('file_path')
				if path:
					yield path
		return
	except Exception:
		pass

	# 2) Fallback to DB folder walk
	folder = _get_patient_folder_from_db(patient_id)
	if not folder or not os.path.exists(folder):
		logger.warning(f"No accessible folder for patient {patient_id}: {folder}")
		return
	try:
		# Optional study filter via cheap tag read
		try:
			import pydicom
		except Exception:
			pydicom = None
		count = 0
		for root, _dirs, files in os.walk(folder):
			for name in files:
				if not name.lower().endswith(('.dcm', '.dicom')) and '.' in name:
					continue
				path = os.path.join(root, name)
				if study_uid and pydicom is not None:
					try:
						ds = pydicom.dcmread(path, stop_before_pixels=True, specific_tags=['StudyInstanceUID'])
						if str(getattr(ds, 'StudyInstanceUID', '')) != str(study_uid):
							continue
					except Exception:
						# If tag unreadable, include; OHIF/Orthanc will group later
						pass
				yield path
				count += 1
				if count >= hard_limit:
					return
	except Exception as e:
		logger.error(f"Error iterating DICOM files: {e}")


def _create_patient_zip(patient_id: str, study_uid: Optional[str] = None) -> Optional[str]:
	"""Create a temporary ZIP with patient (or study) DICOMs; returns file path or None."""
	tmp_dir = tempfile.mkdtemp(prefix=f"dicom_{patient_id}_")
	zip_path = os.path.join(tmp_dir, f"{patient_id}{'_' + study_uid if study_uid else ''}.zip")
	total = 0
	try:
		with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
			for fpath in _iter_dicom_files(patient_id, study_uid, hard_limit=5000):
				try:
					# Keep relative path inside patient's folder when possible
					folder = _get_patient_folder_from_db(patient_id) or ''
					arcname = os.path.relpath(fpath, folder) if folder and fpath.startswith(folder) else os.path.basename(fpath)
					# Normalize backslashes for zip
					arcname = arcname.replace('\\', '/')
					zf.write(fpath, arcname)
					total += 1
				except Exception:
					continue
		if total == 0:
			return None
		return zip_path
	except Exception as e:
		logger.error(f"Failed to create ZIP: {e}")
		return None


def _orthanc_is_available() -> bool:
	"""Return True if the configured Orthanc server appears reachable."""
	try:
		r = requests.get(f"{ORTHANC_URL.rstrip('/')}/system", timeout=5, auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD))
		return r.status_code == 200
	except Exception:
		return False


def _get_orthanc_archive_stream(patient_id: str, study_uid: Optional[str] = None):
	"""Try to obtain a streaming archive (ZIP) from Orthanc for the given patient or study.

	Returns a tuple (response_obj, filename) when successful, or (None, None) on failure.
	The caller is responsible for closing the response (response.close()).
	"""
	# If Orthanc isn't available, bail early
	try:
		if not _orthanc_is_available():
			return None, None
	except Exception:
		return None, None

	# If study UID provided, try that first
	try:
		if study_uid:
			arc_url = f"{ORTHANC_URL.rstrip('/')}/studies/{study_uid}/archive"
			r = requests.get(arc_url, auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD), stream=True, timeout=60)
			if r.status_code == 200:
				# Orthanc serves a zip; determine filename if present
				cd = r.headers.get('Content-Disposition', '')
				fname = None
				if 'filename=' in cd:
					try:
						fname = cd.split('filename=')[-1].strip('"')
					except Exception:
						fname = None
				if not fname:
					fname = f"orthanc_study_{study_uid}.zip"
				return r, fname
	except Exception:
		pass

	# No study UID given or failed: try to locate a study for the patient
	try:
		# List patients in Orthanc and match by PatientID in MainDicomTags
		patients_url = f"{ORTHANC_URL.rstrip('/')}/patients"
		resp = requests.get(patients_url, auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD), timeout=10)
		if resp.status_code != 200:
			return None, None
		for orthanc_patient_id in resp.json():
			try:
				p = requests.get(f"{ORTHANC_URL.rstrip('/')}/patients/{orthanc_patient_id}", auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD), timeout=10).json()
				pid = p.get('MainDicomTags', {}).get('PatientID', '')
				if str(pid) == str(patient_id):
					# get studies for this orthanc patient
					studs = p.get('Studies') or []
					if isinstance(studs, list) and len(studs) > 0:
						chosen = studs[0]
						arc_url = f"{ORTHANC_URL.rstrip('/')}/studies/{chosen}/archive"
						r2 = requests.get(arc_url, auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD), stream=True, timeout=60)
						if r2.status_code == 200:
							fname = f"orthanc_patient_{patient_id}_study_{chosen}.zip"
							return r2, fname
			except Exception:
				continue
	except Exception:
		pass

	return None, None


def _safe_import_subblueprint(module_name: str, attr: str) -> Optional[Blueprint]:
	"""Try to import <attr> from <module_name> and return it if available.

	Try a relative import first (package local), then attempt an absolute
	import under ``backend.routes``. This makes the registrar tolerant to
	different application start points (running from repo root vs module).
	"""
	# 1) Try package-relative import (e.g. .discovery)
	try:
		module = __import__(f".{module_name}", globals(), locals(), [attr])
		bp = getattr(module, attr)
		if isinstance(bp, Blueprint):
			return bp
		logger.warning("%s.%s exists but is not a Blueprint", module_name, attr)
	except Exception:
		logger.debug("Package-relative import failed for %s.%s", module_name, attr)

	# 2) Try absolute import under backend.routes (e.g. backend.routes.discovery)
	try:
		module = __import__(f"backend.routes.{module_name}", fromlist=[attr])
		bp = getattr(module, attr)
		if isinstance(bp, Blueprint):
			return bp
		logger.warning("backend.routes.%s.%s exists but is not a Blueprint", module_name, attr)
	except Exception:
		logger.debug("Absolute import fallback failed for backend.routes.%s.%s", module_name, attr)

	return None


# Try to import the commonly available sub-blueprints; missing modules
# are non-fatal and will be logged. This keeps nas_core import-safe.
_discovery_bp = _safe_import_subblueprint('discovery', 'discovery_bp')
_devices_bp = _safe_import_subblueprint('devices', 'devices_bp')
_indexing_bp = _safe_import_subblueprint('indexing', 'indexing_bp')
_legacy_nas_bp = _safe_import_subblueprint('nas_routes_backup_old', 'nas_bp')

logger.info(f"🔍 Blueprint import results: discovery={_discovery_bp is not None}, devices={_devices_bp is not None}, indexing={_indexing_bp is not None}, legacy={_legacy_nas_bp is not None}")


def _register_available_subblueprints():
	"""Register any sub-blueprints we successfully imported.

	Called at module import time so that ``nas_core_bp`` ends up with the
	expected children when the app registers it. We keep this isolated so
	unit tests can patch or inspect it easily.
	"""
	if _discovery_bp:
		nas_core_bp.register_blueprint(_discovery_bp, url_prefix='')
		logger.debug('Registered discovery blueprint onto nas_core_bp')
	else:
		logger.info('discovery blueprint not available; skipping')

	if _devices_bp:
		nas_core_bp.register_blueprint(_devices_bp, url_prefix='')
		logger.debug('Registered devices blueprint onto nas_core_bp')
	else:
		logger.info('devices blueprint not available; skipping')

	if _indexing_bp:
		nas_core_bp.register_blueprint(_indexing_bp, url_prefix='')
		logger.info('✅ Registered indexing blueprint onto nas_core_bp')
	else:
		logger.warning('⚠️ indexing blueprint not available; skipping')

	# Backwards compatibility: register legacy nas_routes blueprint if present
	if _legacy_nas_bp:
		nas_core_bp.register_blueprint(_legacy_nas_bp, url_prefix='')
		logger.info('✅ Registered legacy nas_routes onto nas_core_bp for compatibility')
	else:
		logger.warning('⚠️ legacy nas_routes not available; skipping')


# perform registration now (safe no-op when imports were missing)
_register_available_subblueprints()


@nas_core_bp.route('/_routes', methods=['GET'])
def _list_nas_routes():
	"""Return a small JSON list of routes belonging to this blueprint.

	This endpoint is intended for debugging and discovery during
	development. It is only allowed when the application debug mode is
	enabled or when ``NAS_CORE_EXPOSE_ROUTES`` is explicitly True.
	"""
	app = current_app._get_current_object()
	allowed = app.config.get('NAS_CORE_EXPOSE_ROUTES', app.debug)
	if not allowed:
		return jsonify({'error': 'route listing disabled'}), 403

	rules = []
	prefix = nas_core_bp.name + '.'
	for rule in app.url_map.iter_rules():
		if rule.endpoint.startswith(prefix):
			view = app.view_functions.get(rule.endpoint)
			doc = (view.__doc__ or '').strip().splitlines()[0] if view and view.__doc__ else ''
			rules.append({
				'rule': rule.rule,
				'methods': sorted([m for m in rule.methods if m not in ('HEAD', 'OPTIONS')]),
				'endpoint': rule.endpoint,
				'doc': doc,
			})

	return jsonify({'routes': rules})


@nas_core_bp.route('/dashboard/status', methods=['GET'])
def get_dashboard_status():
	"""Get overall dashboard status for NAS integration"""
	try:
		from datetime import datetime, timedelta
		import sqlite3

		# Get live indexing status by calling the local indexing status endpoint first
		indexing_status = None
		try:
			import requests as _req
			_idx_url = request.host_url.rstrip('/') + '/api/nas/indexing/status'
			_r = _req.get(_idx_url, timeout=5)
			if _r.ok:
				_json = _r.json()
				# /api/nas/indexing/status returns { success: True, status: { ... } }
				indexing_status = _json.get('status') or _json
			else:
				indexing_status = None
		except Exception:
			indexing_status = None

		# If HTTP returned a dict but it's missing some UI-expected keys, try to enrich it
		if isinstance(indexing_status, dict):
			# Ensure auto_indexing exists and other helpful keys are present by using the safe helper
			try:
				import importlib
				idx_mod = importlib.import_module('backend.routes.indexing')
				safe = idx_mod.get_indexing_status_safe()
				if isinstance(safe, dict):
					# Merge missing keys from safe into the HTTP result without overwriting existing values
					for k, v in safe.items():
						if k not in indexing_status or indexing_status.get(k) is None:
							indexing_status[k] = v
			except Exception:
				# If enrichment fails, ensure we at least have a sane auto_indexing object
				indexing_status.setdefault('auto_indexing', {'monitoring': False, 'mounted_shares': 0, 'last_check': None})

		# Fallback: import the internal helper if HTTP call didn't return usable data
		if not isinstance(indexing_status, dict):
			# Import the indexing module and read its in-memory state directly
			try:
				import importlib
				idx_mod = importlib.import_module('backend.routes.indexing')
				# Make a shallow copy to avoid mutating the module's state
				indexing_state_live = dict(getattr(idx_mod, 'indexing_state', {}) or {})
				# Enrich with DB-derived safe status if available
				try:
					safe = idx_mod.get_indexing_status_safe()
					if isinstance(safe, dict):
						indexing_state_live.update(safe)
				except Exception:
					pass
				indexing_status = indexing_state_live
			except Exception as _e:
				indexing_status = {'total_patients': 0, 'is_running': False, 'progress': 0, 'details': f'Indexing status error: {_e}'}

		# Ensure we have a dict
		if not isinstance(indexing_status, dict):
			indexing_status = {'total_patients': 0, 'is_running': False, 'progress': 0, 'details': 'Indexing status missing'}

		# Compute quick counts (today, yesterday, this week) from metadata DB
		quick_counts = {'today': 0, 'yesterday': 0, 'week': 0}
		try:
			from ..metadata_db import get_metadata_db_path
			meta_db = get_metadata_db_path()
			conn = sqlite3.connect(meta_db, timeout=10)
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()

			now = datetime.now()
			today = now.strftime('%Y%m%d')
			yesterday = (now - timedelta(days=1)).strftime('%Y%m%d')
			week_start = (now - timedelta(days=now.weekday())).strftime('%Y%m%d')

			def count_on_date(d):
				try:
					# Normalize study_date stored values by removing any dashes before comparison
					cur.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies WHERE REPLACE(study_date, '-', '') = ?", (d,))
					r = cur.fetchone()
					if r and r[0]:
						return int(r[0])
				except Exception:
					pass
				# fallback to patients view (YYYY-MM-DD)
				dd = f"{d[0:4]}-{d[4:6]}-{d[6:8]}".strip()
				try:
					# Ensure we compare trimmed values in the patients view as well
					cur.execute('SELECT COUNT(*) FROM patients WHERE TRIM(first_study_date) = ? OR TRIM(last_study_date) = ?', (dd, dd))
					r2 = cur.fetchone()
					return int(r2[0]) if r2 and r2[0] else 0
				except Exception:
					return 0

			quick_counts['today'] = count_on_date(today)
			quick_counts['yesterday'] = count_on_date(yesterday)
			try:
				cur.execute('SELECT COUNT(DISTINCT patient_id) FROM patient_studies WHERE study_date >= ?', (week_start,))
				rw = cur.fetchone()
				quick_counts['week'] = int(rw[0]) if rw and rw[0] else 0
			except Exception:
				try:
					ws = f"{week_start[0:4]}-{week_start[4:6]}-{week_start[6:8]}"
					cur.execute('SELECT COUNT(*) FROM patients WHERE first_study_date >= ?', (ws,))
					rw2 = cur.fetchone()
					quick_counts['week'] = int(rw2[0]) if rw2 and rw2[0] else 0
				except Exception:
					quick_counts['week'] = 0
			conn.close()
		except Exception:
			# leave defaults if DB not accessible
			pass

		# Orthanc status
		try:
			import requests
			orthanc_response = requests.get('http://localhost:8042/system', timeout=5)
			orthanc_connected = orthanc_response.status_code == 200
		except Exception:
			orthanc_connected = False

		dashboard = {
			'quick_counts': quick_counts,
			'indexing': indexing_status,
			# Provide a top-level auto_indexing object for the frontend UI (backwards compatibility)
			'auto_indexing': indexing_status.get('auto_indexing') if isinstance(indexing_status, dict) else {
				'monitoring': False,
				'mounted_shares': 0,
				'last_check': None,
				'active': False
			},
			# Ensure indexing object includes auto_mode (used for icons) and last_updated
			
			'orthanc': {'connected': orthanc_connected, 'url': 'http://localhost:8042'},
			'timestamp': datetime.now().isoformat(),
			'system_status': 'operational',
			'services': {
				'nas_integration': True,
				'patient_indexing': indexing_status.get('is_running', False),
				'orthanc_pacs': orthanc_connected
			}
		}

		return jsonify({'success': True, 'dashboard': dashboard})

	except Exception as e:
		import logging
		logger = logging.getLogger(__name__)
		logger.error(f'Dashboard status error: {e}')
		return jsonify({'success': False, 'error': str(e), 'system_status': 'error', 'timestamp': datetime.now().isoformat()}), 500


@nas_core_bp.route('/search/patient', methods=['POST'])
def search_patient_comprehensive():
	"""Enhanced patient search using refactored services"""
	try:
		data = request.get_json() or {}

		# Normalize inputs: map generic payload (query/search_type) to explicit fields
		query = (data.get('query') or '').strip()
		search_type = (data.get('search_type') or '').strip().lower()
		patient_id = (data.get('patient_id') or '').strip()
		patient_name = (data.get('patient_name') or '').strip()
		study_date = (data.get('study_date') or '').strip()
		limit = int(data.get('limit') or 50)

		# If the caller used the simplified API, map it accordingly
		if query and not (patient_id or patient_name or study_date):
			if search_type in ('patient_id', 'id'):
				patient_id = query
			elif search_type in ('patient_name', 'name'):
				patient_name = query
			elif search_type in ('study_date', 'date'):
				study_date = query

		# Build normalized payload for the service
		normalized_payload = {
			'patient_id': patient_id,
			'patient_name': patient_name,
			'study_date': study_date,
			'limit': limit
		}

		# Try to use our refactored search service
		try:
			import sys
			import os
			
			# Add path to medical-reporting-module (best-effort)
			# Compute the Orthanc repo root (4 levels up from this file)
			orthanc_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
			medical_module_path = os.path.join(orthanc_root, 'medical-reporting-module')
			if medical_module_path not in sys.path:
				sys.path.insert(0, medical_module_path)
			
			# Robust import: prefer backend.services.nas_patient_search, then fallback to services.nas_patient_search
			search_service_func = None
			try:
				from backend.services import nas_patient_search as _ns
				search_service_func = _ns.search_patient_comprehensive
			except Exception:
				try:
					from services import nas_patient_search as _ns2
					search_service_func = _ns2.search_patient_comprehensive
				except Exception:
					# Last resort: import the function directly from backend.services
					from backend.services import search_patient_comprehensive as _fn
					search_service_func = _fn
			
			logger.info(f"🔍 Using refactored patient search service")
			results = search_service_func(normalized_payload)

			# Enforce exact-match filtering when searching by patient_id to prevent mismatches
			if patient_id:
				exact = [p for p in results.get('patients', []) if p.get('patient_id') == patient_id]
				# If we found exact matches, prefer them; otherwise, try contains match as fallback
				if exact:
					results['patients'] = exact[:limit]
				else:
					contains = [p for p in results.get('patients', []) if patient_id in (p.get('patient_id') or '')]
					results['patients'] = contains[:limit]

				results['total_found'] = len(results['patients'])
			
			return jsonify(results)
			
		except ImportError as ie:
			logger.warning(f"Refactored search service not available: {ie}")
			# Fallback to basic search
			return jsonify({
				'success': True,
				'patients': [],
				'total_found': 0,
				'message': 'Search service temporarily unavailable',
				'fallback': True
			})
			
	except Exception as e:
		logger.error(f'Patient search error: {e}')
		return jsonify({
			'success': False,
			'error': str(e),
			'patients': [],
			'total_found': 0
		}), 500


@nas_core_bp.route('/search/suggestions', methods=['GET'])
def get_search_suggestions():
	"""Smart autocomplete suggestions API - like Google search suggestions"""
	try:
		# Get query parameters
		query = request.args.get('q', '').strip()
		suggestion_type = request.args.get('type', 'all')  # names, ids, dates, modalities, or all
		limit = min(int(request.args.get('limit', '10')), 20)  # Max 20 suggestions
		
		if not query:
			return jsonify({'error': 'Query parameter "q" is required'}), 400
		
		# Import the smart search service
		# Import from local services module
		from backend.services.patient_search import get_smart_suggestions
		
		logger.info(f"🔍 Getting suggestions for: '{query}' (type: {suggestion_type})")
		results = get_smart_suggestions(query, suggestion_type, limit)
		
		return jsonify(results)
		
	except Exception as e:
		logger.error(f'Suggestions API error: {e}')
		import traceback
		logger.error(f'Traceback: {traceback.format_exc()}')
		return jsonify({
			'success': False,
			'error': str(e),
			'suggestions': {
				'patient_names': [],
				'patient_ids': [],
				'study_dates': [],
				'modalities': []
			}
		}), 500


@nas_core_bp.route('/search/stats', methods=['GET'])
def get_search_stats():
	"""Get database statistics for search UI"""
	try:
		# Import the smart search service
		import sys
		import os
		
		# Add path to medical-reporting-module 
		# Simple stats from database
		from backend.services.database_operations import get_database_connection
		
		conn = get_database_connection()
		cursor = conn.cursor()
		
		# Count patients
		cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patients")
		total_patients = cursor.fetchone()[0]
		
		# Count studies
		cursor.execute("SELECT COUNT(*) FROM patient_studies")
		total_studies = cursor.fetchone()[0]
		
		conn.close()
		
		results = {
			'success': True,
			'total_patients': total_patients,
			'total_studies': total_studies,
			'total_series': 0,
			'total_instances': 0
		}
		
		return jsonify(results)
		
	except Exception as e:
		logger.error(f'Stats API error: {e}')
		return jsonify({
			'success': False,
			'error': str(e)
		}), 500


@nas_core_bp.route('/orthanc/import', methods=['POST'])
def import_to_orthanc():
	"""Push a patient's DICOM files from NAS into Orthanc, returns summary and a study UID if detected.

	body: { patient_id: str, study_uid?: str, limit?: int }
	"""
	try:
		data = request.get_json() or {}
		patient_id = (data.get('patient_id') or '').strip()
		study_uid = (data.get('study_uid') or '').strip() or None
		hard_limit = int(data.get('limit') or 2000)
		if not patient_id:
			return jsonify({'success': False, 'error': 'patient_id is required'}), 400

		imported = 0
		first_study_uid = None
		errors = 0

		for i, fpath in enumerate(_iter_dicom_files(patient_id, study_uid, hard_limit=hard_limit)):
			try:
				with open(fpath, 'rb') as fh:
					resp = requests.post(
						f"{ORTHANC_URL.rstrip('/')}/instances",
						data=fh,
						auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
						headers={'Content-Type': 'application/dicom'},
						timeout=120,
					)
				if resp.status_code in (200, 201):
					imported += 1
					if not first_study_uid:
						try:
							meta = resp.json()
							first_study_uid = meta.get('ParentStudy') or meta.get('StudyInstanceUID')
						except Exception:
							pass
				else:
					errors += 1
			except Exception as e:
				logger.debug(f"Import failed for {fpath}: {e}")
				errors += 1

		return jsonify({
			'success': True,
			'imported': imported,
			'errors': errors,
			'patient_id': patient_id,
			'study_uid': study_uid or first_study_uid,
			'dicomweb': f"{request.host_url.rstrip('/')}/api/nas/dicom-web"
		})
	except Exception as e:
		logger.error(f"Orthanc import error: {e}")
		return jsonify({'success': False, 'error': str(e)}), 500


@nas_core_bp.route('/export/cloud', methods=['POST'])
def export_to_cloud():
	"""Create a ZIP for a patient's DICOMs and upload to OneDrive or Google Drive.

	body: { patient_id: str, study_uid?: str, provider: 'onedrive'|'gdrive', folder?: str, make_public?: bool }
	Requires an access token via env var: ONEDRIVE_ACCESS_TOKEN or GOOGLE_DRIVE_ACCESS_TOKEN.
	Returns a shareable link when possible.
	"""
	try:
		data = request.get_json() or {}
		patient_id = (data.get('patient_id') or '').strip()
		study_uid = (data.get('study_uid') or '').strip() or None
		provider = (data.get('provider') or '').lower()
		folder = (data.get('folder') or 'MedicalImages').strip() or 'MedicalImages'
		make_public = bool(data.get('make_public', True))
		if not patient_id or provider not in ('onedrive', 'gdrive'):
			return jsonify({'success': False, 'error': 'patient_id and valid provider are required'}), 400

		zip_path = _create_patient_zip(patient_id, study_uid)
		if not zip_path or not os.path.exists(zip_path):
			# Try to return helpful debugging info: folder path from DB if available
			folder = None
			try:
				folder = _get_patient_folder_from_db(patient_id)
			except Exception:
				folder = None
			msg = 'No DICOM files found to export'
			if folder:
				msg = f"{msg}; attempted folder: {folder}"
			logger.info(f"Cloud export failed for patient {patient_id}: {msg}")
			return jsonify({'success': False, 'error': msg, 'attempted_folder': folder}), 404

		file_name = os.path.basename(zip_path)
		size = os.path.getsize(zip_path)

		if provider == 'onedrive':
			# Prefer environment token, else fall back to saved OAuth token file
			token = os.environ.get('ONEDRIVE_ACCESS_TOKEN') or os.environ.get('MICROSOFT_GRAPH_TOKEN')
			if not token:
				try:
					stored = _load_onedrive_token()
					if stored and isinstance(stored, dict):
						token = stored.get('access_token') or stored.get('accessToken')
				except Exception:
					token = None
			if not token:
				logger.info(f"OneDrive export failed for patient {patient_id}: missing token")
				return jsonify({'success': False, 'error': 'OneDrive token missing. Please connect OneDrive via /api/nas/onedrive/setup or set ONEDRIVE_ACCESS_TOKEN.'}), 400
			# If Orthanc is available, attempt to stream the archive directly from Orthanc to OneDrive
			orthanc_resp = None
			orthanc_fname = None
			try:
				orthanc_resp, orthanc_fname = _get_orthanc_archive_stream(patient_id, study_uid)
			except Exception:
				orthanc_resp = None

			# Decide upload source: stream from Orthanc response if available, else use local ZIP file
			if orthanc_resp:
				# Stream upload to OneDrive using requests.put with streaming body
				up_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder}/{orthanc_fname}:/content"
				r = requests.put(up_url, headers={'Authorization': f'Bearer {token}'}, data=orthanc_resp.iter_content(chunk_size=8192))
				# Close Orthanc response
				try:
					orthanc_resp.close()
				except Exception:
					pass
				resp = r
			else:
				# Upload via PUT to root:/folder/filename:/content using local ZIP
				up_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder}/{file_name}:/content"
				with open(zip_path, 'rb') as fh:
					resp = requests.put(up_url, headers={'Authorization': f'Bearer {token}'}, data=fh)
			if resp.status_code not in (200, 201):
				return jsonify({'success': False, 'error': f'OneDrive upload failed: {resp.status_code} {resp.text[:200]}'}), 502
			item = resp.json()
			share_link = None
			if make_public:
				try:
					create_link_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item['id']}/createLink"
					cl = requests.post(create_link_url, json={'type': 'view', 'scope': 'anonymous'}, headers={'Authorization': f'Bearer {token}'} )
					if cl.status_code in (200, 201):
						share_link = cl.json().get('link', {}).get('webUrl')
				except Exception:
					share_link = None
			# If we created a local ZIP (orthanc_resp not used) ensure cleanup of temp files
			try:
				if not orthanc_resp and zip_path and os.path.exists(zip_path):
					tmpd = os.path.dirname(zip_path)
					# remove zip and temp dir
					try:
						os.remove(zip_path)
					except Exception:
						pass
					try:
						os.rmdir(tmpd)
					except Exception:
						pass
			except Exception:
				pass
			return jsonify({'success': True, 'provider': 'onedrive', 'file_id': item.get('id'), 'size': size, 'share_link': share_link})

		elif provider == 'gdrive':
			token = os.environ.get('GOOGLE_DRIVE_ACCESS_TOKEN') or os.environ.get('GDRIVE_TOKEN')
			if not token:
				return jsonify({'success': False, 'error': 'Google Drive token missing. Set GOOGLE_DRIVE_ACCESS_TOKEN.'}), 400
			# Multipart upload (metadata + media)
			boundary = '-------dicomboundary'
			meta = {
				'name': file_name,
			}
			# Optional: create/locate folder by name is more involved; skipping for brevity
			with open(zip_path, 'rb') as fh:
				media = fh.read()
			body = (
				f'--{boundary}\r\n'
				'Content-Type: application/json; charset=UTF-8\r\n\r\n'
				f'{__import__("json").dumps(meta)}\r\n'
				f'--{boundary}\r\n'
				'Content-Type: application/zip\r\n\r\n'
				+ media.decode('latin1', errors='ignore') + '\r\n'
				f'--{boundary}--'
			)
			up = requests.post(
				'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
				headers={'Authorization': f'Bearer {token}', 'Content-Type': f'multipart/related; boundary={boundary}'},
				data=body
			)
			if up.status_code not in (200, 201):
				return jsonify({'success': False, 'error': f'Google Drive upload failed: {up.status_code} {up.text[:200]}'}), 502
			item = up.json()
			share_link = None
			if make_public:
				try:
					perm = requests.post(
						f"https://www.googleapis.com/drive/v3/files/{item['id']}/permissions",
						headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
						json={'role': 'reader', 'type': 'anyone'}
					)
					if perm.status_code in (200, 201):
						# Get webViewLink
						getf = requests.get(
							f"https://www.googleapis.com/drive/v3/files/{item['id']}?fields=webViewLink,webContentLink",
							headers={'Authorization': f'Bearer {token}'}
						)
						if getf.status_code == 200:
							data_j = getf.json()
							share_link = data_j.get('webViewLink') or data_j.get('webContentLink')
				except Exception:
					share_link = None
			return jsonify({'success': True, 'provider': 'gdrive', 'file_id': item.get('id'), 'size': size, 'share_link': share_link})

	except Exception as e:
		logger.error(f"Cloud export error: {e}")
		return jsonify({'success': False, 'error': str(e)}), 500


@nas_core_bp.route('/search/ui', methods=['GET'])
def smart_search_ui():
	"""Serve the smart patient search interface"""
	try:
		import os
		from flask import send_file
		
		# Get the path to the HTML file
		html_path = os.path.join(
			os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
			'frontend', 'smart_patient_search.html'
		)
		
		if os.path.exists(html_path):
			return send_file(html_path)
		else:
			return jsonify({
				'error': 'Smart search UI not found',
				'path': html_path
			}), 404
			
	except Exception as e:
		logger.error(f'Smart search UI error: {e}')
		return jsonify({'error': str(e)}), 500


@nas_core_bp.route('/download/patient', methods=['GET'])
def download_patient_dicom():
	"""Download DICOM files for a patient or specific study"""
	try:
		patient_id = request.args.get('patient_id')
		study_uid = request.args.get('study_uid')

		# Default to serving a single DICOM file instead of ZIP (users requested no ZIP by default)
		format_type = request.args.get('format', 'raw')  # 'zip'|'raw'|'tar' (raw -> single file)

		if not patient_id:
			return jsonify({'error': 'patient_id parameter is required'}), 400

		# Import the download service robustly. We try standard package import first,
		# then fall back to locating the "medical-reporting-module" folder by walking
		# upward from this file and loading the service module from disk.
		import sys
		import os
		import importlib.util

		try:
			try:
				from services.dicom_download_service import download_patient_studies
			except Exception:
				# Locate the medical-reporting-module directory by walking up the tree
				search_dir = os.path.abspath(os.path.dirname(__file__))
				medical_module_path = None
				for _ in range(6):
					candidate = os.path.join(search_dir, 'medical-reporting-module')
					if os.path.isdir(candidate):
						medical_module_path = candidate
						break
					parent = os.path.dirname(search_dir)
					if parent == search_dir:
						break
					search_dir = parent

				if not medical_module_path:
					# As a last resort, check one level above the repo root
					candidate = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'medical-reporting-module'))
					if os.path.isdir(candidate):
						medical_module_path = candidate

				if medical_module_path and medical_module_path not in sys.path:
					sys.path.insert(0, medical_module_path)

				# Try import again after adjusting sys.path
				try:
					from services.dicom_download_service import download_patient_studies
				except Exception:
					# Final fallback: load by file path
					service_file = None
					if medical_module_path:
						service_file = os.path.join(medical_module_path, 'services', 'dicom_download_service.py')
					# Also allow for likely relative locations
					if not service_file or not os.path.exists(service_file):
						possible = [
							os.path.join(os.path.dirname(__file__), '..', '..', 'medical-reporting-module', 'services', 'dicom_download_service.py'),
							os.path.join(os.path.dirname(__file__), '..', '..', '..', 'medical-reporting-module', 'services', 'dicom_download_service.py')
						]
						for p in possible:
							p = os.path.abspath(p)
							if os.path.exists(p):
								service_file = p
								break

					if service_file and os.path.exists(service_file):
						spec = importlib.util.spec_from_file_location('dicom_download_service', service_file)
						module = importlib.util.module_from_spec(spec)
						spec.loader.exec_module(module)
						download_patient_studies = getattr(module, 'download_patient_studies')
					else:
						raise ImportError('Could not locate dicom_download_service file')

		except Exception as e:
			logger.error(f'DICOM download error: {e}')
			return jsonify({'success': False, 'error': 'Download service unavailable', 'details': str(e)}), 500

		logger.info(f"📥 Download request for patient: {patient_id}, study: {study_uid}")

		# Get the download file path and metadata
		result = download_patient_studies(patient_id, study_uid, format_type)

		if result.get('success'):
			from flask import send_file

			# Send the file for download
			return send_file(
				result['file_path'],
				as_attachment=True,
				download_name=result.get('filename'),
				mimetype=result.get('mimetype', 'application/octet-stream')
			)
		else:
			return jsonify(result), 404

	except Exception as e:
		logger.error(f'DICOM download error: {e}')
		return jsonify({
			'success': False,
			'error': str(e)
		}), 500


@nas_core_bp.route('/search/dicom-files', methods=['POST'])
def search_dicom_files():
	"""Search for DICOM files for a specific patient"""
	try:
		data = request.get_json() or {}
		patient_id = data.get('patient_id')
		folder_path = data.get('folder_path')
		
		if not patient_id:
			return jsonify({
				'success': False,
				'error': 'Patient ID is required'
			}), 400
		
		logger.info(f"🔍 Searching DICOM files for patient: {patient_id}")
		
		# Try to find DICOM files in the NAS system
		try:
			import sys
			import os
			
			# Add path to medical-reporting-module 
			orthanc_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
			medical_module_path = os.path.join(orthanc_root, 'medical-reporting-module')
			if medical_module_path not in sys.path:
				sys.path.insert(0, medical_module_path)
			
			# Try importing the DICOM search service; fall back to loading by file path
			try:
				from services import nas_dicom_search
				dicom_files = nas_dicom_search.find_patient_dicom_files(patient_id, folder_path)
			except Exception:
				import importlib.util
				# Ensure import paths are available
				project_root = orthanc_root
				nasintegration_path = os.path.join(project_root, 'NASIntegration') if os.path.basename(project_root) != 'NASIntegration' else project_root
				if nasintegration_path not in sys.path:
					sys.path.insert(0, nasintegration_path)
				if medical_module_path not in sys.path:
					sys.path.insert(0, medical_module_path)
				service_file = os.path.join(medical_module_path, 'services', 'nas_dicom_search.py')
				if os.path.exists(service_file):
					spec = importlib.util.spec_from_file_location('nas_dicom_search', service_file)
					module = importlib.util.module_from_spec(spec)
					spec.loader.exec_module(module)
					dicom_files = module.find_patient_dicom_files(patient_id, folder_path)
				else:
					raise
			
			return jsonify({
				'success': True,
				'files': dicom_files,
				'total_files': len(dicom_files),
				'patient_id': patient_id
			})
			
		except ImportError as ie:
			logger.warning(f"DICOM search service not available: {ie}")
			
			# Fallback: search in the current NAS system
			if folder_path and os.path.exists(folder_path):
				# Try to enrich with DICOM metadata to enable proper slice sorting
				dicom_files = []
				try:
					import pydicom
				except Exception:
					pydicom = None
				max_scan = 500  # limit for performance
				count = 0
				for root, dirs, files in os.walk(folder_path):
					for file in files:
						if not file.lower().endswith(('.dcm', '.dicom')):
							continue
						file_path = os.path.join(root, file)
						file_size = 0
						try:
							file_size = os.path.getsize(file_path)
						except Exception:
							pass

						meta = {
							'filename': file,
							'file_path': file_path,
							'file_size': file_size,
							'relative_path': os.path.relpath(file_path, folder_path),
							'instance_number': None,
							'slice_location': None,
							'image_position_patient_z': None,
							'series_instance_uid': None,
							'study_instance_uid': None
						}

						# Extract minimal metadata without pixel data if possible
						if pydicom is not None:
							try:
								ds = pydicom.dcmread(file_path, stop_before_pixels=True, specific_tags=['InstanceNumber','ImagePositionPatient','SliceLocation','SeriesInstanceUID','StudyInstanceUID'])

								# InstanceNumber
								inst = getattr(ds, 'InstanceNumber', None)
								if inst is not None:
									try:
										meta['instance_number'] = int(inst)
									except Exception:
										pass

								# ImagePositionPatient Z
								ipp = getattr(ds, 'ImagePositionPatient', None)
								if ipp and len(ipp) >= 3:
									try:
										meta['image_position_patient_z'] = float(ipp[2])
									except Exception:
										pass

								# SliceLocation
								sloc = getattr(ds, 'SliceLocation', None)
								if sloc is not None:
									try:
										meta['slice_location'] = float(sloc)
									except Exception:
										pass

								# UIDs
								meta['series_instance_uid'] = getattr(ds, 'SeriesInstanceUID', None)
								meta['study_instance_uid'] = getattr(ds, 'StudyInstanceUID', None)
							except Exception:
								pass

						dicom_files.append(meta)
						count += 1
						if count >= max_scan:
							break
					if count >= max_scan:
						break
				
				# Sort using metadata when available: IPP Z, then SliceLocation, then InstanceNumber, then filename natural
				def _file_sort_key(item):
					z = item.get('image_position_patient_z')
					sloc = item.get('slice_location')
					inst = item.get('instance_number')
					fname = item.get('filename') or ''
					# Extract trailing number from filename as last resort
					import re
					nums = re.findall(r"(\d+)", fname)
					fnum = int(nums[-1]) if nums else 0
					return (
						float('inf') if z is None else z,
						float('inf') if sloc is None else sloc,
						float('inf') if inst is None else inst,
						fnum
					)

				dicom_files_sorted = sorted(dicom_files, key=_file_sort_key)
				limited = dicom_files_sorted[:50]
				return jsonify({
					'success': True,
					'files': limited,
					'total_files': len(dicom_files_sorted),
					'patient_id': patient_id
				})
			else:
				return jsonify({
					'success': False,
					'files': [],
					'total_files': 0,
					'message': 'No DICOM files found for this patient'
				})
		
	except Exception as e:
		logger.error(f'DICOM file search error: {e}')
		return jsonify({
			'success': False,
			'error': str(e),
			'files': []
		}), 500


@nas_core_bp.route('/dicom/image', methods=['POST'])
def serve_dicom_image():
	"""Serve a DICOM file as an image"""
	try:
		data = request.get_json() or {}
		file_path = data.get('file_path')
		patient_id = data.get('patient_id')
		
		if not file_path or not os.path.exists(file_path):
			return jsonify({
				'success': False,
				'error': 'DICOM file not found'
			}), 404
		
		logger.info(f"🖼️ Serving DICOM image: {file_path}")
		
		# Try to convert DICOM to viewable format
		try:
			import pydicom
			from PIL import Image
			import numpy as np
			from io import BytesIO
			
			# Read DICOM file
			ds = pydicom.dcmread(file_path)
			
			# Get pixel data
			if hasattr(ds, 'pixel_array'):
				pixel_array = ds.pixel_array
				
				# Normalize to 0-255 range
				if pixel_array.max() > 255:
					pixel_array = ((pixel_array - pixel_array.min()) / 
								   (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
				
				# Convert to PIL Image
				if len(pixel_array.shape) == 2:  # Grayscale
					image = Image.fromarray(pixel_array, mode='L')
				else:
					image = Image.fromarray(pixel_array)
				
				# Convert to PNG
				img_buffer = BytesIO()
				image.save(img_buffer, format='PNG')
				img_buffer.seek(0)
				
				return send_file(
					img_buffer,
					mimetype='image/png',
					as_attachment=False
				)
			else:
				return jsonify({
					'success': False,
					'error': 'No image data in DICOM file'
				}), 400
				
		except ImportError:
			logger.warning("DICOM processing libraries not available")
			# Fallback: serve the raw DICOM file
			return send_file(
				file_path,
				mimetype='application/dicom',
				as_attachment=False
			)
		
	except Exception as e:
		logger.error(f'DICOM image serving error: {e}')
		return jsonify({
			'success': False,
			'error': str(e)
		}), 500


# -----------------------------
# NAS→Orthanc Auto-Import Control
# -----------------------------

@nas_core_bp.route('/import/start-auto', methods=['POST'])
def start_auto_import():
	"""Start the automatic NAS→Orthanc import service"""
	try:
		from services.nas_orthanc_importer import get_importer
		importer = get_importer()
		
		if importer.running:
			return jsonify({
				'success': False,
				'message': 'Auto-import service is already running'
			})
		
		importer.start_background_import()
		
		return jsonify({
			'success': True,
			'message': 'Auto-import service started',
			'status': 'running'
		})
		
	except Exception as e:
		logger.error(f'Failed to start auto-import: {e}')
		return jsonify({
			'success': False,
			'error': str(e)
		}), 500


@nas_core_bp.route('/import/stop-auto', methods=['POST'])
def stop_auto_import():
	"""Stop the automatic NAS→Orthanc import service"""
	try:
		from services.nas_orthanc_importer import get_importer
		importer = get_importer()
		
		if not importer.running:
			return jsonify({
				'success': False,
				'message': 'Auto-import service is not running'
			})
		
		importer.stop_background_import()
		
		return jsonify({
			'success': True,
			'message': 'Auto-import service stopped',
			'status': 'stopped'
		})
		
	except Exception as e:
		logger.error(f'Failed to stop auto-import: {e}')
		return jsonify({
			'success': False,
			'error': str(e)
		}), 500


@nas_core_bp.route('/import/status', methods=['GET'])
def get_import_status():
	"""Get the status of the auto-import service"""
	try:
		from services.nas_orthanc_importer import get_importer
		importer = get_importer()
		
		# Get Orthanc patient count
		orthanc_patient_count = 0
		try:
			response = requests.get(
				f"{ORTHANC_URL}/patients",
				auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
				timeout=5
			)
			if response.status_code == 200:
				orthanc_patient_count = len(response.json())
		except:
			pass
		
		# Get NAS patient count from database
		nas_patient_count = 0
		try:
			import sqlite3
			# Robust import: try relative package import first
			try:
				from ..metadata_db import get_metadata_db_path
			except Exception:
				try:
					from services.metadata_db import get_metadata_db_path
				except Exception:
					from metadata_db import get_metadata_db_path
			conn = sqlite3.connect(get_metadata_db_path(), timeout=5)
			cursor = conn.cursor()
			cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies WHERE patient_id IS NOT NULL")
			nas_patient_count = cursor.fetchone()[0]
			conn.close()
		except:
			pass
		
		return jsonify({
			'success': True,
			'running': importer.running,
			'status': 'running' if importer.running else 'stopped',
			'orthanc_patients': orthanc_patient_count,
			'nas_patients': nas_patient_count,
			'remaining': nas_patient_count - orthanc_patient_count
		})
		
	except Exception as e:
		logger.error(f'Failed to get import status: {e}')
		return jsonify({
			'success': False,
			'error': str(e)
		}), 500


@nas_core_bp.route('/import/run-now', methods=['POST'])
def run_import_now():
	"""Run one import cycle immediately"""
	try:
		from services.nas_orthanc_importer import get_importer
		importer = get_importer()
		
		# Run import cycle in current thread (blocking)
		importer.run_import_cycle()
		
		return jsonify({
			'success': True,
			'message': 'Import cycle completed'
		})
		
	except Exception as e:
		logger.error(f'Failed to run import: {e}')
		return jsonify({
			'success': False,
			'error': str(e)
		}), 500


def register_nas_blueprints(app, url_prefix: str = '/api/nas'):
	"""Convenience: register the NAS core blueprint on the given Flask app.

	This helper keeps application setup code concise and centralizes the
	prefix used for the NAS API.
	"""
	logger.debug('Registering nas_core_bp on app with prefix %s', url_prefix)
@nas_core_bp.route('/search/suggestions', methods=['GET'])
def get_patient_suggestions():
    q = request.args.get('q', '').strip()
    type_filter = request.args.get('type', 'all')
    limit = int(request.args.get('limit', 15))
    
    logger.info(f"🔍 Getting suggestions for: '{q}' (type: {type_filter})")
    
    try:
        from ..services.patient_search import get_smart_suggestions
        suggestions = get_smart_suggestions(q, type_filter, limit)
        return jsonify(suggestions)
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        return jsonify({'error': str(e)}), 500


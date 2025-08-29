"""Minimal NAS indexer (Phase 0)

Safe, non-destructive scanner that inspects a filesystem path for DICOM files,
extracts basic metadata and computes a SHA-256 hash. Does not modify databases
or post to Orthanc when run in dry-run mode.

Usage (programmatic):
  from indexer.indexer import scan_path
  result = scan_path("/path/to/nas", dry_run=True)

This file is intentionally small and dependency-light. It attempts to import
pydicom but will return a helpful error if the library is not installed.
"""

from typing import List, Dict, Any, Optional
import os
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

try:
    import pydicom
    from pydicom.errors import InvalidDicomError
    PYDICOM_AVAILABLE = True
except Exception:
    PYDICOM_AVAILABLE = False


def _sha256_of_file(path: str, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            h.update(chunk)
    return h.hexdigest()


def _try_read_dicom(path: str) -> Optional[Dict[str, Any]]:
    if not PYDICOM_AVAILABLE:
        raise RuntimeError('pydicom is not installed; please pip install pydicom')

    try:
        # fast read: only metadata (stop before pixel data)
        ds = pydicom.dcmread(path, stop_before_pixels=True, force=False)
        return {
            'StudyInstanceUID': str(ds.get('StudyInstanceUID', '')),
            'SeriesInstanceUID': str(ds.get('SeriesInstanceUID', '')),
            'SOPInstanceUID': str(ds.get('SOPInstanceUID', '')),
            'PatientID': str(ds.get('PatientID', '')),
            'PatientName': str(ds.get('PatientName', '')),
            'StudyDate': str(ds.get('StudyDate', '')),
            'Modality': str(ds.get('Modality', ''))
        }
    except InvalidDicomError:
        return None
    except Exception as e:
        # Could be other parsing errors; log and skip
        logger.debug(f"Failed to read DICOM {path}: {e}")
        return None


def scan_path(root_path: str, max_files: int = 100, dry_run: bool = True) -> Dict[str, Any]:
    """Scan a filesystem path for DICOM files.

    Returns a dict with keys: scanned_count, candidates (list), errors (list).
    Each candidate includes nas_path, file_size, file_hash, and any found UIDs.
    """
    result = {'scanned_count': 0, 'candidates': [], 'errors': []}

    if not os.path.exists(root_path):
        return { 'error': f'Path does not exist: {root_path}' }

    seen = 0
    for dirpath, dirs, files in os.walk(root_path):
        for fname in files:
            if seen >= max_files:
                return result
            fpath = os.path.join(dirpath, fname)
            result['scanned_count'] += 1
            try:
                # Quick heuristic: look at extension or try reading as DICOM
                is_candidate = False
                if fname.lower().endswith('.dcm'):
                    is_candidate = True
                else:
                    # Check small header for DICM marker as cheap test
                    try:
                        with open(fpath, 'rb') as fh:
                            fh.seek(128)
                            marker = fh.read(4)
                            if marker == b'DICM':
                                is_candidate = True
                    except Exception:
                        pass

                if not is_candidate:
                    # try pydicom read (may be slower) - but only if available
                    if PYDICOM_AVAILABLE:
                        meta = _try_read_dicom(fpath)
                        if meta:
                            is_candidate = True
                    else:
                        is_candidate = False

                if not is_candidate:
                    continue

                # We have a candidate; extract metadata and hash
                meta = None
                if PYDICOM_AVAILABLE:
                    meta = _try_read_dicom(fpath)

                file_size = os.path.getsize(fpath)
                file_hash = _sha256_of_file(fpath)

                candidate = {
                    'nas_path': fpath,
                    'file_size': file_size,
                    'file_hash': file_hash,
                    'metadata': meta or {},
                }

                result['candidates'].append(candidate)
                seen += 1

            except Exception as e:
                logger.debug(f"Error scanning file {fpath}: {e}")
                result['errors'].append({ 'file': fpath, 'error': str(e) })

    return result


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser(description='Minimal NAS indexer (dry-run)')
    p.add_argument('--path', '-p', required=True, help='Root path to scan')
    p.add_argument('--max', type=int, default=100, help='Maximum files to inspect')
    p.add_argument('--dry-run', action='store_true', default=True, help='Only report, do not import')

    args = p.parse_args()
    out = scan_path(args.path, max_files=args.max, dry_run=args.dry_run)
    print(json.dumps(out, indent=2))

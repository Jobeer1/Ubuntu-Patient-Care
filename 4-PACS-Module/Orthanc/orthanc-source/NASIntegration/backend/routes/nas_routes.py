"""Compatibility shim: expose legacy `nas_bp` under the expected module name

This module intentionally keeps the import simple so that the dynamic
import logic in `nas_core._safe_import_subblueprint('nas_routes', 'nas_bp')`
will succeed. If the legacy implementation cannot be imported we fall back
to an empty placeholder blueprint so the application does not crash at
import-time.
"""
import logging
from flask import Blueprint

logger = logging.getLogger(__name__)

# Try to import the legacy implementation from the backup file. We support
# both package-relative and absolute import paths so this shim is robust to
# different start points.
try:
    # Package-relative import (preferred when running the backend package)
    from .nas_routes_backup_old import nas_bp  # type: ignore
    logger.info('Imported nas_bp from nas_routes_backup_old (package-relative)')
except Exception:
    try:
        # Absolute import fallback
        from backend.routes.nas_routes_backup_old import nas_bp  # type: ignore
        logger.info('Imported nas_bp from backend.routes.nas_routes_backup_old (absolute)')
    except Exception:
        # Fallback: expose an empty blueprint so imports succeed but endpoints
        # will be effectively no-ops until the legacy implementation is
        # restored.
        logger.exception('Failed to import legacy nas_routes_backup_old; creating placeholder nas_bp')
        nas_bp = Blueprint('nas', __name__, url_prefix='/api/nas')

__all__ = ['nas_bp']

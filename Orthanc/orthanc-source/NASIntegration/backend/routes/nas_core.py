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
from flask import Blueprint, current_app, jsonify
from typing import Optional

logger = logging.getLogger(__name__)

# Primary blueprint object kept for backward compatibility with imports
nas_core_bp = Blueprint('nas_core', __name__)


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


def register_nas_blueprints(app, url_prefix: str = '/api/nas'):
	"""Convenience: register the NAS core blueprint on the given Flask app.

	This helper keeps application setup code concise and centralizes the
	prefix used for the NAS API.
	"""
	logger.debug('Registering nas_core_bp on app with prefix %s', url_prefix)
	app.register_blueprint(nas_core_bp, url_prefix=url_prefix)


__all__ = ['nas_core_bp', 'register_nas_blueprints']


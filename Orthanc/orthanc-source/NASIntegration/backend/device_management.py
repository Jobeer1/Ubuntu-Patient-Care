"""Compatibility facade for the refactored device management modules.

This file preserves the legacy import surface. It tries several import
strategies so code that imports this module as a top-level module (for
example when running ``app.py`` directly) and code that imports it as a
package (``backend.device_management``) both work.

Import order attempted:
 - relative imports (``.core`` / ``.models``)
 - local imports (``core`` / ``models`` if the backend folder is on sys.path)
 - absolute imports (``backend.core`` / ``backend.models``)

If none succeed the module raises ImportError with guidance.
"""

from typing import Tuple


def _import_core() -> Tuple[type, object]:
	"""Import DeviceManager and device_manager from available locations."""
	# 1) Try relative import (package import)
	try:
		from .core import DeviceManager, device_manager  # type: ignore
		return DeviceManager, device_manager
	except Exception:
		pass

	# 2) Try local (when module is loaded as top-level from backend dir)
	try:
		from core import DeviceManager, device_manager  # type: ignore
		return DeviceManager, device_manager
	except Exception:
		pass

	# 3) Try absolute import
	try:
		# Ensure parent directory is on sys.path so 'backend' package can be imported
		import os, sys
		this_dir = os.path.dirname(__file__)
		parent_dir = os.path.dirname(this_dir)
		if parent_dir and parent_dir not in sys.path:
			sys.path.insert(0, parent_dir)

		from backend.core import DeviceManager, device_manager  # type: ignore
		return DeviceManager, device_manager
	except Exception as e:
		raise ImportError(
			"Could not import DeviceManager/device_manager. Tried '.core', 'core', and 'backend.core'."
		) from e


def _import_models():
	"""Import MedicalDevice from available locations."""
	try:
		from .models import MedicalDevice  # type: ignore
		return MedicalDevice
	except Exception:
		pass

	try:
		from models import MedicalDevice  # type: ignore
		return MedicalDevice
	except Exception:
		pass

	try:
		from backend.models import MedicalDevice  # type: ignore
		return MedicalDevice
	except Exception as e:
		raise ImportError(
			"Could not import MedicalDevice. Tried '.models', 'models', and 'backend.models'."
		) from e


DeviceManager, device_manager = _import_core()
MedicalDevice = _import_models()

__all__ = ["DeviceManager", "device_manager", "MedicalDevice"]
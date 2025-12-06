#!/usr/bin/env python3
"""Study routes - lightweight Find Studies page

This provides a simple search UI for DICOM studies. If an Orthanc backend
is configured the page can be extended to call it; for now this offers a
usable local search and friendly UX.
"""
from flask import render_template, current_app
import logging

logger = logging.getLogger(__name__)


def render_find_studies():
    try:
        return render_template('find_studies.html')
    except Exception:
        logger.exception('Failed to render find_studies.html')
        return ('<h3>Find Studies</h3><p>This feature is currently being updated. Please try again later.</p>')

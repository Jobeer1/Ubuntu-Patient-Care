#!/usr/bin/env python3
"""
Wrapper template for Device Management.

This file composes the final DEVICE_MANAGEMENT_TEMPLATE by importing the
two smaller parts produced during the refactor. Keeping each file under
800 lines improves maintainability.
"""

from .device_management_part1 import DEVICE_MANAGEMENT_TEMPLATE_PART1
from .device_management_part2 import DEVICE_MANAGEMENT_TEMPLATE_PART2


DEVICE_MANAGEMENT_TEMPLATE = DEVICE_MANAGEMENT_TEMPLATE_PART1 + DEVICE_MANAGEMENT_TEMPLATE_PART2
